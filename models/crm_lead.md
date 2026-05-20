# Analyse des performances – Vue Kanban CRM (`crm_case_kanban_view_leads`)

## Contexte

La vue Pipeline (kanban des opportunités) met environ 1 seconde à s'afficher.
Ce document décrit comment mesurer précisément ce temps, puis comment identifier et traiter les sources de lenteur.

---

## Mesure réelle (18 mai 2026)

Résultats obtenus via **Firefox DevTools → Réseau → Analyse des performances** :

| Métrique | Valeur |
|----------|--------|
| Durée totale de chargement | **3,66 s** |
| Dont requêtes XHR (17 req.) | **2,87 s** |
| Dont images (11) | 0,76 s |
| Taille totale transférée | 1 640 Ko |

### Détail des requêtes `web_search_read` sur `crm.lead`

8 requêtes parallèles, une par colonne kanban visible :

| Requête | Durée |
|---------|-------|
| `web_search_read` colonne 1 | 389 ms |
| `web_search_read` colonne 2 | 173 ms |
| `web_search_read` colonne 3 | 320 ms |
| `web_search_read` colonne 4 | 331 ms |
| `web_search_read` colonne 5 | 376 ms |
| `web_search_read` colonne 6 | 310 ms |
| `web_search_read` colonne 7 | 371 ms |
| `web_search_read` colonne 8 | 404 ms |

**Conclusion** : les 8 `web_search_read` représentent à eux seuls ~2,4 s, soit **65 % du temps total**.
Les autres appels (`read_progress_bar` 13 ms, `web_read_group` 18 ms, `get_views` 35 ms) sont négligeables.

Le problème est donc **la quantité de données chargées par colonne**, pas le nombre de requêtes
(elles s'exécutent en parallèle). Chaque requête dure entre 173 ms et 404 ms côté serveur.

---

## 1. Mesurer précisément le temps de chargement dans le navigateur

### 1.1 Onglet Réseau – Firefox DevTools (procédure pas à pas)

> **Important** : l'onglet Réseau n'enregistre que les requêtes émises **après** son ouverture.
> Il faut donc ouvrir DevTools *avant* de naviguer vers le Pipeline.

**Étape 1 — Préparer la capture**

1. Appuyer sur **F12** pour ouvrir DevTools → cliquer sur l'onglet **Réseau**
2. Vérifier que le bouton d'enregistrement (cercle ⏺ en haut à gauche de l'onglet) est actif (rouge = enregistrement en cours). S'il est grisé, cliquer dessus.
3. Dans la barre de filtre de type, cliquer sur **XHR** pour n'afficher que les requêtes AJAX.
4. Laisser le champ de recherche textuel **vide** pour l'instant (effacer "multiread" s'il est présent).

**Étape 2 — Déclencher le chargement**

5. Depuis une autre page Odoo (ex. Contacts), cliquer sur le menu **CRM → Pipeline** pour déclencher le chargement complet de la vue kanban.  
   *(Ne pas faire F5 sur le Pipeline lui-même : cela recharge toute l'application et mélange les requêtes d'init.)*

**Étape 3 — Analyser les requêtes**

6. Une liste de requêtes apparaît. Les trier par **Durée** (cliquer sur l'en-tête de colonne) pour voir les plus lentes en premier.
7. Identifier les appels coûteux :
   - `web_search_read` sur `crm.lead` → lecture des enregistrements de chaque colonne
   - `read_group` sur `crm.lead` → agrégation des totaux (barre de progression)
   - `web_read_group` sur `crm.lead` → groupement par `stage_id`
   - requêtes sur `mail.activity` → chargement des activités

8. Pour filtrer uniquement les appels Odoo : saisir **`call_kw`** dans le champ de recherche textuel.

**Étape 4 — Inspecter une requête lente**

9. Cliquer sur une requête → onglet **En-têtes** pour voir l'URL, **Réponse** pour le JSON retourné, et **Minutage** pour le détail (attente serveur vs transfert réseau).

**Étape 5 — Mesurer le temps total perçu**

10. La ligne **DOMContentLoaded** (en bleu) et **Chargé** (en rouge) visibles en bas de l'onglet Réseau donnent le temps total de chargement de la page.  
    Pour une mesure plus précise : cliquer sur l'icône chronomètre ⏱ → **"Ajouter un marqueur de performance"** avant de naviguer.

### 1.2 Onglet Performance (Chrome DevTools)

1. Onglet **Performance** → cliquer sur l'icône **Record** (⏺)
2. Déclencher la navigation vers le Pipeline
3. Arrêter l'enregistrement
4. Identifier dans la flamme les fonctions JS lentes (rendering OWL, rendering des cartes kanban, calcul des progressbars)

### 1.3 Mode debug Odoo + logs SQL côté serveur

Activer le mode debug Odoo :
```
http://localhost:8069/web?debug=1
```

Activer les logs SQL dans la configuration Odoo :
```ini
[options]
log_handler = odoo.sql_db:DEBUG
```
ou au lancement :
```bash
./odoo-bin --log-handler=odoo.sql_db:DEBUG
```

Cela affiche dans les logs chaque requête SQL avec son temps d'exécution.
Filtrer les lignes avec `crm_lead` pour isoler les requêtes du Pipeline.

### 1.4 Utiliser l'outil `explain analyze` PostgreSQL

Depuis `psql`, lancer sur les requêtes identifiées :
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT ... FROM crm_lead WHERE ...;
```
Vérifier que les index sont bien utilisés (pas de `Seq Scan` sur de grandes tables).

---

## 2. Analyse du payload `web_search_read` (données réelles)

Payload capturé pour la colonne `stage_id = 3` (Visite Planifiée), 293 ms :

```
domain  : [["type","=","opportunity"], ["stage_id","=",3]]
limit   : 80
order   : "" (→ utilise _order du modèle : sequence, priority desc, id desc)
```

### Champs demandés (`specification`)

| Champ | Type | Observation |
|-------|------|-------------|
| `stage_id` | Many2one | léger |
| `probability` | Float | léger |
| `active` | Boolean | léger |
| `company_currency` | Many2one | léger |
| `recurring_revenue_monthly` | Float **calculé** | peut être coûteux |
| `team_id` | Many2one | léger |
| `color` | Integer | léger |
| `name` | Char | léger |
| `expected_revenue` | Float | léger |
| `partner_id` | Many2one | léger |
| `tag_ids` | **Many2many** | jointure sur `crm_lead_tag_rel` + `crm_tag` |
| `lead_properties` | **JSON dynamique** | ⚠️ suspect principal |
| `priority` | Selection | léger |
| `activity_ids` | **Many2many** (IDs uniquement) | jointure `mail_activity` |
| `activity_exception_decoration` | Calculé | dépend des activités |
| `activity_exception_icon` | Calculé | dépend des activités |
| `activity_state` | Calculé | dépend des activités |
| `activity_summary` | Calculé | dépend des activités |
| `activity_type_icon` | Calculé | dépend des activités |
| `activity_type_id` | Many2one calculé | dépend des activités |
| `user_id` | Many2one | léger |

**Constat important** : aucun champ `is_*` du module personnalisé n'est présent dans la specification.
Le module `is_jura_energie_solaire_18` **n'a aucun impact** sur le temps de chargement du kanban.

### Points de charge identifiés

**1. `lead_properties` (suspect principal)**  
Champ JSON de propriétés dynamiques configurables par l'utilisateur. Pour chaque enregistrement,
Odoo doit désérialiser le JSON et résoudre les définitions de propriétés depuis `ir.model.fields`.
Multiplié par jusqu'à 80 enregistrements × 8 colonnes = **640 évaluations**.  
Si aucune propriété dynamique n'est configurée ni utilisée, ce champ ne sert à rien dans le kanban.

**2. 6 champs `activity_*` calculés**  
`activity_state`, `activity_summary`, `activity_exception_*`, `activity_type_*` sont tous calculés
à partir de `mail.activity`. Bien qu'Odoo les regroupe probablement en une seule jointure, c'est
6 colonnes calculées par enregistrement.

**3. `tag_ids` (Many2many)**  
Jointure sur `crm_lead_tag_rel` puis `crm_tag`. Rapide si les index sont en place.

**4. Tri `sequence, priority DESC, id DESC`**  
Le champ `order` est vide dans le payload → le serveur utilise `_order` du modèle, soit
`sequence, priority desc, id desc`. Ce tri sur 3 colonnes nécessite un index composite.

---

## 3. Sources de lenteur – analyse mise à jour

### 3.1 `lead_properties` ⚠️ Priorité haute

Ce champ est dans la `specification` de chaque `web_search_read`. Il est présent dans la vue kanban
standard d'Odoo 18 :
```xml
<field name="lead_properties" widget="properties"/>
```
Si aucune propriété dynamique n'est définie pour `crm.lead`, ce champ retourne un tableau vide
mais Odoo effectue tout de même la résolution côté serveur.

**Action** : tester en ajoutant dans `is_jura_energie_solaire_18` un xpath qui retire ce champ du kanban :
```xml
<xpath expr="//field[@name='lead_properties']" position="replace"/>
```

### 3.2 Champs `activity_*` calculés

6 champs calculés liés aux activités sont chargés pour chaque enregistrement. Ils sont nécessaires
pour l'icône d'activité sur chaque carte. La jointure sur `mail.activity` doit être rapide si
l'index `(res_model, res_id)` existe.

Vérifier en base :
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'mail_activity'
  AND indexdef ILIKE '%res_id%';
```

### 3.3 Tri `sequence, priority DESC, id DESC`

Le champ `sequence` a été ajouté par le module pour le drag-and-drop. Le tri sur 3 colonnes
sans index composite force un tri en mémoire sur chaque requête.

Vérifier / créer l'index :
```sql
-- Vérifier si l'index existe
SELECT indexname FROM pg_indexes
WHERE tablename = 'crm_lead'
  AND indexdef ILIKE '%sequence%';

-- Créer si absent
CREATE INDEX IF NOT EXISTS crm_lead_sequence_priority_id_idx
ON crm_lead (sequence, priority DESC, id DESC);
```

### 3.4 `tag_ids` (Many2many)

Vérifier l'index sur la table de relation :
```sql
SELECT indexname FROM pg_indexes
WHERE tablename = 'crm_lead_tag_rel';
```

### 3.5 Nombre d'enregistrements par colonne

`limit: 80` est la valeur par défaut. Si une colonne approche les 80 enregistrements,
la requête est plus lourde. Vérifier le nombre réel par colonne :
```sql
SELECT stage_id, COUNT(*) as nb
FROM crm_lead
WHERE type = 'opportunity' AND active = true
GROUP BY stage_id
ORDER BY nb DESC;
```

---

## 4. Plan d'action recommandé

| # | Action | Effort | Gain estimé |
|---|--------|--------|-------------|
| 1 | **Retirer `lead_properties` du kanban** via xpath | 5 min | ⭐⭐⭐ Élevé |
| 2 | **Créer l'index** `(sequence, priority, id)` | 5 min | ⭐⭐ Moyen |
| 3 | Vérifier l'index `mail_activity (res_model, res_id)` | 5 min | ⭐⭐ Moyen |
| 4 | Vérifier le nombre d'enregistrements par colonne | 2 min | Diagnostic |
| 5 | Activer logs SQL (`odoo.sql_db:DEBUG`) pour mesurer après les changements | 10 min | Validation |

L'action 1 est à tester en priorité : si `lead_properties` est la cause principale,
le gain sera immédiatement visible dans l'onglet Réseau (durée des `web_search_read` réduite).

---

## 5. Références

- [Odoo Performance Guidelines](https://www.odoo.com/documentation/18.0/developer/reference/backend/performance.html)
- [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/sql-explain.html)
- Firefox DevTools Network : F12 → Réseau → filtrer XHR → trier par Durée

