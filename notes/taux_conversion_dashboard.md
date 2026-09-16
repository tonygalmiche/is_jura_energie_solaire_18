# Taux de conversion sur le tableau de bord "Suivi Général"

## Demande client (Jura Energie Solaire)

Sur le tableau de bord "Suivi commercial > Suivi Général" (nouveau) :
- Afficher le taux de conversion depuis début 2026, par secteur.
- Taux de conversion = total vendu / (total vendu + total perdu).
- Graphique par mois.
- Vue également par année.

## Contexte technique

- Le client utilise le module générique **`is_tableau_de_bord18`** (modules-generiques), pas l'app Spreadsheet Dashboard.
- Ce module affiche des tuiles (liste / graphique / pivot / kanban) branchées sur des recherches enregistrées (`ir.filters`), avec une seule mesure par tuile (le choix d'agrégateur somme/moyenne/min/max/count existe dans le modèle mais n'est pas exposé dans le formulaire de configuration d'une ligne — en pratique c'est toujours une somme ou un count) — voir `models/is_tableau_de_bord.py`.
- Il ne sait pas calculer un ratio entre deux comptages (gagné vs perdu) sur des domaines différents : un développement est nécessaire.
- Champs existants côté CRM (`is_jura_energie_solaire_18/models/crm_lead.py`) :
  - `is_secteur` : secteur de l'opportunité (`SECTEUR_SELECTION`).
  - Gagné/perdu : à définir sur `stage_id.is_won = True` (gagné) et `active = False` + `probability = 0` (perdu), selon la configuration des étapes CRM du client.

## Besoin multi-critères

Le client veut découper le taux par secteur, sous-secteur, vendeur, mois, année (et combinaisons). Un modèle précalculé à maille fixe (ex. secteur × mois) ne convient pas : un taux ne se ré-agrège pas après coup (contrairement à un compteur), donc pas évolutif si la maille de découpe change.

## Solution retenue — extension de `is_tableau_de_bord18`

Réutiliser l'infra de groupby déjà existante (`graph_groupbys`, qui gère déjà 1 ou 2 groupements — `controllers/main.py:1225`) :
- Nouveau champ sur la ligne : `ratio_won_domain` (domaine Odoo définissant "gagné", ex. `[('stage_id.is_won','=',True)]`).
- Le domaine du filtre existant (`filter_id`) définit le total (gagné + perdu).
- Le contrôleur fait deux `read_group` groupés par les mêmes `graph_groupbys` (secteur, sous-secteur, vendeur, mois, année, ou 2 combinés) : un sur le domaine total, un sur total + gagné. Calcule `%` = gagné/total par groupe. Réutilise le rendu Chart.js existant.
- Évolutif : ajouter un nouveau critère de découpe ne demande aucun code, juste changer la config de la ligne (groupby = champ Odoo standard).
- Limite assumée : 2 dimensions de groupby max, comme le graphique standard actuel (pas de vrai pivot 3D).

## Solution finale retenue : 1 filtre + 2 regroupements + 2 champs (numérateur/dénominateur)

Pistes précédentes écartées : un domaine texte est trop technique pour un non-développeur ; 2 recherches enregistrées séparées (Gagné/Perdu) font courir un risque d'incohérence si elles ne partagent pas exactement la même base (période, portée).

Solution retenue : un seul filtre de base (une simple liste, pas de regroupement particulier requis) qui définit l'univers de données (ex. "Opportunités depuis le 01/01/2026"), puis 4 champs de configuration sur la ligne :
- **Regroupement 1** / **Regroupement 2** : deux sélecteurs conviviaux (liste déroulante de champs du modèle, + une granularité jour/semaine/mois/année si le champ choisi est une date), au lieu de taper du texte technique. En interne, ces 2 sélections calculent automatiquement le champ existant `graph_groupbys` (aujourd'hui un `Char` texte libre, ex. `create_date:month`), exactement comme `_onchange_filter_id` le fait déjà depuis le contexte d'un filtre.
  - Soit jusqu'à 4 champs au total (champ + granularité, ×2), mais la granularité n'apparaît que si le regroupement choisi est une date. Pour l'exemple "par mois et par secteur" : 3 champs à remplir (Regroupement 1 = date, sa granularité = mois, Regroupement 2 = secteur sans granularité).
- **Champs numérateur** : une **liste** de champs à sommer pour le numérateur (ex. `Gagné`).
- **Champs dénominateur** : une **liste** de champs à sommer pour le dénominateur (ex. `Gagné` + `Perdu`), au lieu d'un total calculé implicitement (numérateur + dénominateur). Plus flexible : le dénominateur n'est pas obligé d'être le complément du numérateur, on peut composer n'importe quelle combinaison de champs.

Avantages :
- Un seul filtre = plus de risque d'incohérence entre 2 recherches enregistrées séparées.
- Sélection de champs dans des listes déroulantes = accessible à un non-développeur (comme `field_ids` en mode Liste), pas de domaine à taper.
- Un seul `read_group` (`fields=['is_won:sum','is_perdu:sum']`, `groupby=[regroupement1, regroupement2]`) donne toutes les valeurs nécessaires en un appel ; le calcul fait ensuite `somme(champs numérateur) / somme(champs dénominateur)`.

Prérequis technique : les champs choisis comme numérateur/dénominateur doivent être des champs numériques ou booléens sommables. Sur `crm.lead`, "gagné" n'existe pas comme champ direct (c'est `stage_id.is_won`) : il faudra ajouter un petit champ calculé stocké dédié (ex. `is_won` related à `stage_id.is_won`, `is_perdu` calculé sur `active=False` + `probability=0`). Ce n'est pas un problème en soi — l'essentiel est que l'utilisateur final n'ait ensuite qu'à choisir "Gagné" / "Perdu" dans une liste déroulante, sans rien savoir de leur construction technique.

Les listes déroulantes "Champs numérateur" / "Champs dénominateur" devront être filtrées pour ne proposer que les champs réellement sommables (`integer`, `float`, `monetary`, éventuellement `boolean` stocké) — à l'exclusion des champs texte, relations, dates, etc. qui n'ont pas de sens dans une somme.

### Exemple concret : "taux par mois"

**1. Un seul filtre enregistré** sur `crm.lead` : "Opportunités depuis 01/01/2026" (liste simple, toutes étapes, gagnées et perdues incluses).

**2. Configuration de la ligne :**
| Champ | Valeur |
|---|---|
| Mode d'affichage | Graphique |
| Type de graphique | Barres |
| Recherche enregistrée | Opportunités depuis 01/01/2026 |
| Regroupement 1 | `create_date:month` |
| Champs numérateur | Gagné (`is_won`) |
| Champs dénominateur | Gagné (`is_won`) + Perdu (`is_perdu`) |

**3. Résultat** (1 `read_group` groupé par mois, calcul du %) :

| Mois | Gagné | Perdu | Total | Taux |
|---|---|---|---|---|
| Janvier 2026 | 8 | 12 | 20 | 40% |
| Février 2026 | 12 | 6 | 18 | 67% |
| Mars 2026 | 15 | 7 | 22 | 68% |

Pour ajouter le secteur : Regroupement 2 = `is_secteur` → barres empilées par secteur et par mois, sans code supplémentaire.

## Étape 1 (faite) — champs génériques de regroupement et de mesure

Implémenté dans `is_tableau_de_bord18` v18.0.2.0.7 (branché uniquement sur `display_mode = 'graph'` pour l'instant, pensé pour être réutilisé par Pivot/Liste plus tard) :
- `groupby_field_1_id` / `groupby_period_1` / `groupby_field_2_id` / `groupby_period_2` : sélecteurs conviviaux qui calculent automatiquement `graph_groupbys` (passé en lecture seule).
- `measure_field_id` : sélecteur convivial qui calcule automatiquement `graph_measure` (passé en lecture seule).

## Solution finale v2 — champ "Type de mesure" (Compteur / Somme / Taux)

Idée retenue pour unifier `measure_field_id` (étape 1) et le besoin de taux, au lieu d'une case à cocher "Afficher comme un taux" séparée :
- Nouveau champ **`measure_type`** (Selection : Compteur / Somme / Taux, défaut Compteur).
  - **Compteur** : aucun champ supplémentaire (équivaut à `measure_field_id` vide aujourd'hui).
  - **Somme** : affiche `measure_field_id` (déjà existant depuis l'étape 1).
  - **Taux** : affiche deux sélecteurs multi-champs **numérateur** / **dénominateur** (`Many2many('ir.model.fields')`, widget `many2many_tags`, filtrés sur les types sommables : integer/float/monetary/boolean), chacun étant la somme d'une liste de champs — ex. numérateur = Gagné, dénominateur = Gagné + Perdu.
- Avantage : un seul concept de "mesure" pour tous les cas (avant : agrégateur technique jamais exposé + case à cocher taux séparée). Rend `avg`/`min`/`max` de `graph_aggregator` caducs, ils n'étaient de toute façon jamais accessibles dans le formulaire.
- Reste basé sur un seul filtre + Regroupement 1/2 existants (pas de filtre dupliqué, pas de risque d'incohérence).

## À trancher

Date de référence pour le regroupement mensuel/annuel : création de l'opportunité ou passage en gagné/perdu ?
