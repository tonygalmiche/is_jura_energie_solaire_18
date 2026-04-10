# Image de fond PDF - Journal des tentatives

> **Date** : 10 avril 2026  
> **Module** : `is_jura_energie_solaire_18`  
> **Objectif** : Afficher une image de papier-en-tête (logo JES + coordonnées + bandeau vert) en fond sur **toutes les pages** de tous les rapports PDF, couvrant header, body ET footer.  
> **Statut** : ✅ Résolu — approche Python PyPDF2 (fusion post-génération)

---

## Sommaire

1. [Contexte technique](#contexte-technique)
2. [Découvertes clés](#découvertes-clés)
3. [Mécanisme natif Odoo 18](#mécanisme-natif-odoo-18)
4. [Tests effectués — chronologie](#tests-effectués--chronologie)
5. [Ce qui a fonctionné](#ce-qui-a-fonctionné)
6. [Ce qui n'a pas fonctionné du tout](#ce-qui-na-pas-fonctionné-du-tout)
7. [Ce qui a fonctionné partiellement](#ce-qui-a-fonctionné-partiellement)
8. [Pistes non explorées](#pistes-non-explorées)
9. [Fichiers impliqués](#fichiers-impliqués)
10. [Configuration actuelle](#configuration-actuelle)

---

## Contexte technique

### Environnement

| Élément | Valeur |
|---------|--------|
| Odoo version | 18.0 |
| VM | `bookworm` (VirtualBox), accessible via `ssh odoo@bookworm` |
| Base de données | `jura-energie-solaire18` |
| Générateur PDF | **wkhtmltopdf** (pas Chromium) — ancien moteur WebKit |
| Config Odoo | `/etc/odoo/jura-energie-solaire18.conf` |
| Addons path (VM) | `/media/sf_dev_odoo/18.0/jura-energie-solaire` (dossier partagé VirtualBox) |
| Addons path (hôte) | `/home/tony/Documents/Développement/dev_odoo/18.0/jura-energie-solaire` |
| Layout société | `web.external_layout_boxed` (view id=202) |

### Paperformat A4

| Paramètre | Valeur |
|-----------|--------|
| margin_top | 52 mm |
| margin_bottom | 32 mm |
| margin_left | 0 |
| margin_right | 0 |
| header_spacing | 52 mm |

### Images de test

- `static/src/img/papier-en-tete-jes.jpg` — 6.6 Ko (réduit)
- `static/src/img/papier-en-tete-jes.png` — 11 Ko (réduit)
- L'image originale fait ~230 Ko en JPG, ~700 Ko en PNG

---

## Découvertes clés

### 1. Architecture des rapports PDF dans wkhtmltopdf

**C'est le point fondamental.** wkhtmltopdf rend **3 documents HTML séparés** pour une seule page PDF :

```
┌──────────────────────┐
│  HEADER HTML         │  ← document HTML séparé avec #minimal_layout_report_headers
│  (margin_top zone)   │
├──────────────────────┤
│  BODY HTML           │  ← document HTML séparé (ni header ni footer)
│  (contenu du rapport)│
├──────────────────────┤
│  FOOTER HTML         │  ← document HTML séparé avec #minimal_layout_report_footers
│  (margin_bottom zone)│
└──────────────────────┘
```

Chaque document est rendu indépendamment à travers le template `web.minimal_layout`. La variable `subst` est `True` pour header/footer, `False` pour body.

**Conséquence** : il est impossible d'avoir un seul élément HTML qui couvre les 3 zones. Toute approche de fond doit être appliquée dans chacune des 3 sections, en décalant la position pour montrer la bonne portion de l'image.

### 2. `_prepare_html()` détruit le `<head>` de `web.report_layout`

La méthode `_prepare_html()` dans `ir_actions_report.py` :
1. Prend le HTML complet rendu par `web.report_layout`
2. Extrait les éléments `.header`, `.footer`, `.article` 
3. Re-rend **chaque morceau** à travers `web.minimal_layout`
4. Le `<head>` original (celui de `web.report_layout`) est **perdu**

**Conséquence** : toute modification CSS dans `<head>` via héritage de `web.report_layout` n'a AUCUN effet sur le PDF final. Il faut hériter de `web.minimal_layout`.

### 3. `web.minimal_layout` est le bon template à hériter

C'est le template qui enveloppe CHAQUE section (header, body, footer) individuellement. Son `<head>` est conservé dans le rendu final.

**Template `web.minimal_layout`** (simplifié) :
```xml
<template id="minimal_layout">
    <html style="height: 0;">
        <head>
            <base t-att-href="base_url"/>
            <!-- assets CSS/JS -->
            <script t-if="subst">function subst() { ... }</script>
        </head>
        <body class="o_body_pdf ..." t-att-onload="subst and 'subst()'">
            <t t-out="body"/>
        </body>
    </html>
</template>
```

IDs importants dans le `body` (injectés par `_prepare_html()`) :
- `#minimal_layout_report_headers` — présent dans le HTML du header
- `#minimal_layout_report_footers` — présent dans le HTML du footer
- Aucun ID spécifique dans le body

### 4. Arguments wkhtmltopdf

```
wkhtmltopdf --disable-local-file-access --quiet \
    --page-size A4 \
    --margin-top 52 --margin-bottom 32 --margin-left 0 --margin-right 0 \
    --header-spacing 52 \
    --javascript-delay 1000 \
    --cookie-jar <fichier_cookie> \
    --header-html <header.html> \
    --footer-html <footer.html> \
    body1.html [body2.html ...] output.pdf
```

- `--disable-local-file-access` : les fichiers locaux (`file://`) sont inaccessibles
- Les cookies de session Odoo sont transmis via `--cookie-jar` → les URL HTTP vers Odoo (`/web/image/...`) **devraient** fonctionner
- `--javascript-delay 1000` : le JS a 1 seconde pour s'exécuter

### 5. Piège bash avec `!important`

En bash, `!important` dans un heredoc NON quoté déclenche l'expansion d'historique (`bash: !important: event not found`). 

**Solution** : utiliser un heredoc avec délimiteur quoté `<< 'XMLEOF'` (pas `<< XMLEOF`) pour empêcher toute expansion.

---

## Mécanisme natif Odoo 18

### ⚠️ Découverte importante en fin de session

Odoo 18 possède **déjà** un mécanisme de fond d'image pour les rapports :

#### Champs sur `res.company` (natifs)

```python
layout_background = fields.Selection(
    [('Blank', 'Blank'), ('Demo logo', 'Demo logo'), ('Custom', 'Custom')],
    default="Blank", required=True
)
layout_background_image = fields.Binary("Background Image")
```

#### Comment ça fonctionne

Chaque template de layout (`external_layout_boxed`, `external_layout_standard`, etc.) applique l'image en fond **sur la `<div>` article** (le body du rapport) :

```xml
<t t-set="layout_background_url"
   t-value="'data:image/png;base64,%s' % company.layout_background_image.decode('utf-8') 
            if company.layout_background_image and company.layout_background == 'Custom' 
            else '/base/static/img/demo_logo_report.png' 
            if company.layout_background == 'Demo logo' 
            else ''" />

<div class="article o_report_layout_boxed ... o_report_layout_background"
     t-attf-style="{{ 'background-image: url(%s);' % layout_background_url if layout_background_url else '' }}">
```

#### CSS associé (`report.scss`)
```scss
.o_report_layout_background {
    background-size: contain;
    background-position: center;
    background-repeat: no-repeat;
}
```

#### Configuration dans l'interface Odoo

Menu : **Paramètres → Général → Mise en page du document** (ou via le Studio de document)

Champs :
- `layout_background` = "Custom"
- `layout_background_image` = uploader l'image

#### Limitation du mécanisme natif

Le fond natif est appliqué **uniquement sur la div article** (zone body), PAS sur le header ni le footer. Il ne couvre donc PAS toute la page A4. C'est le même problème que ce qu'on essaie de résoudre.

**Cependant** : le mécanisme natif utilise un data URI base64 directement en inline style sur une `<div>`, ce qui **fonctionne** (c'est le code natif d'Odoo). Cela prouve que les data URI ne sont pas bloquées en elles-mêmes par wkhtmltopdf.

---

## Tests effectués — chronologie

### Test 1 : `<img>` dans `web.external_layout_boxed`

**Template** : héritage de `web.external_layout_boxed`  
**Méthode** : injection d'un `<img>` avec `position: absolute` dans le layout  
**Résultat** : ❌ **Aucun effet** — l'image n'apparaît pas du tout dans le PDF  
**Raison** : le HTML de `web.external_layout_boxed` est découpé par `_prepare_html()`, l'image est perdue

### Test 2 : CSS `background-image` dans `<head>` de `web.report_layout`

**Template** : héritage de `web.report_layout`  
**Méthode** : ajout de `<style>` avec `background-image` sur `body` dans `<head>`  
**Résultat** : ❌ **Aucun effet**  
**Raison** : le `<head>` de `web.report_layout` est perdu lors du re-rendu par `_prepare_html()`

### Test 3 : `background-color: green` dans `web.report_layout`

**Template** : héritage de `web.report_layout`  
**Méthode** : `background-color: green` sur `body`  
**Résultat** : ❌ **Aucun effet**  
**Raison identique** : `<head>` perdu

### Test 4 : `background-color: green` dans `web.minimal_layout`

**Template** : héritage de `web.minimal_layout`  
**Méthode** : ajout de `<style>body { background-color: green !important; }</style>` dans `<head>`  
**Résultat** : ✅ **Ça marche !** — fond vert visible sur toutes les sections  
**Conclusion** : `web.minimal_layout` est le bon template, le CSS dans son `<head>` est conservé

### Test 5 : `background-image` data URI (grosse image) dans `web.minimal_layout`

**Template** : héritage de `web.minimal_layout`  
**Méthode** : `background-image: url(data:image/png;base64,...)` avec image complète (~230 Ko base64)  
**Résultat** : ❌ **Aucun effet** — le fond reste blanc  
**Hypothèse** : wkhtmltopdf a une limite de taille pour les data URI en CSS background

### Test 6 : `background-image` data URI (petite image 1px rouge)

**Template** : héritage de `web.minimal_layout`  
**Méthode** : data URI d'un PNG 1×1 rouge en `background-image`  
**Résultat** : ✅ **Ça marche** — fond rouge partout  
**Conclusion** : les data URI fonctionnent pour les PETITES images, pas les grandes

### Test 7 : `background-image` data URI (image réduite à ~11 Ko)

**Template** : héritage de `web.minimal_layout`  
**Méthode** : image `papier-en-tete-jes.png` réduite à 11 Ko, base64 ~14 Ko  
**Résultat** : ❌ **Aucun effet**  
**Conclusion** : même 14 Ko de base64 est trop pour `background-image` en CSS dans wkhtmltopdf (ou autre problème)

### Test 8 : `<img>` tag dans body de `web.minimal_layout` (petite 200px)

**Template** : héritage de `web.minimal_layout`  
**Méthode** : ajout d'un `<img>` avec `position: absolute; width: 200px` dans le body via `<xpath expr="//body" position="inside">`  
**Source image** : fichier statique `/is_jura_energie_solaire_18/static/src/img/papier-en-tete-jes.png`  
**Résultat** : ✅ **Ça marche** — l'image de 200px s'affiche  
**Conclusion** : `<img>` fonctionne dans le body de `minimal_layout`, même avec `position: absolute`

### Test 9 : `<img>` tag pleine page avec `position: absolute`

**Template** : héritage de `web.minimal_layout`  
**Méthode** : `<img>` avec `position: absolute; width: 210mm; height: 297mm; top: 0; left: 0; z-index: -1`  
**Source image** : `image_data_uri(env.company.is_pdf_background_image)` (champ Binary dynamique)  
**Résultat** : ⚠️ **Partiellement fonctionnel** — l'image s'affiche dans le body, mais :
- Le header est décalé / mal positionné
- Le footer est encore plus décalé
- L'image ne couvre que la zone body, pas header ni footer
- Problème de z-index : l'image peut couvrir le contenu

### Test 10 : `<img>` dans la section header uniquement (`subst=True`)

**Template** : héritage de `web.minimal_layout`  
**Méthode** : `<img>` injecté conditionnellement quand `subst` est True (header/footer)  
**Résultat** : ⚠️ **L'image s'affiche** mais couvre le contenu du header — le z-index ne fonctionne pas entre les sections HTML séparées de wkhtmltopdf

### Test 11 : `<img>` avec `position: fixed`

**Template** : héritage de `web.minimal_layout`  
**Méthode** : `<img>` avec `position: fixed; width: 210mm; height: 297mm;`  
**Résultat** : ❌ **Aucun effet dans le body** — `position: fixed` ne fonctionne pas dans le body de wkhtmltopdf  
**Note** : `position: fixed` fonctionne dans le header/footer (là où `subst` est True)

### Test 12 : `background-image` via URL HTTP

**Template** : héritage de `web.minimal_layout`  
**Méthode** : `background-image: url(/web/image/res.company/ID/is_pdf_background_image)` sur `body`  
**Avec** : `background-size: 210mm 297mm; background-attachment: fixed`  
**Résultat** : ❌ **Aucun effet** — probablement lié à `--disable-local-file-access` ou autre blocage de wkhtmltopdf pour les URL HTTP sans cookie correct  
**Note** : wkhtmltopdf reçoit un cookie jar, donc les URL HTTP devraient théoriquement fonctionner

### Test 13 : `background-image` via URL HTTP + JavaScript de positionnement

**Template** : héritage de `web.minimal_layout`  
**Méthode** : même que Test 12, avec JS pour détecter header/body/footer et décaler `background-position`  
**Résultat** : ❌ **Même résultat que screenshot** — l'image s'affiche en double dans le header (logo JES en haut + logo JES au milieu), le body n'a pas de fond visible  
**Analyse du screenshot** :
- Header : montre l'image 2 fois (la native Odoo + celle injectée)
- Body : le fond n'apparaît pas ou est mal positionné
- Footer : le fond vert du bas de l'image semble s'afficher correctement

### Test 14 : Inline `style=""` sur `<body>` avec data URI + JS positionnement

**Template** : héritage de `web.minimal_layout`  
**Méthode** : Inspirée du code **natif Odoo** qui met le data URI en attribut `style=""` inline (pas dans `<style>` dans `<head>`). On utilise `<xpath expr="//body" position="attributes">` pour ajouter `t-attf-style` avec `background-image: url(data:image/...)` directement sur `<body>`. Un `<script>` dans `<head>` ajuste `background-position` selon la section (header/body/footer).  
**Code** :
```xml
<xpath expr="//head" position="inside">
    <t t-set="is_bg_data" t-value="image_data_uri(env.company.is_pdf_background_image) 
        if 'is_pdf_background_image' in env.company._fields and env.company.is_pdf_background_image 
        else ''"/>
    <script t-if="is_bg_data">
        document.addEventListener('DOMContentLoaded', function() {
            if (document.getElementById('minimal_layout_report_headers')) {
                document.body.style.backgroundPosition = '0 0';
            } else if (document.getElementById('minimal_layout_report_footers')) {
                document.body.style.backgroundPosition = '0 -265mm';
            } else {
                document.body.style.backgroundPosition = '0 -52mm';
            }
        });
    </script>
</xpath>
<xpath expr="//body" position="attributes">
    <attribute name="t-attf-style">{{ 'background-image: url(%s); background-size: 210mm 297mm; 
        background-repeat: no-repeat; background-position: 0 0; 
        -webkit-print-color-adjust: exact; print-color-adjust: exact;' % is_bg_data 
        if is_bg_data else '' }}</attribute>
</xpath>
```
**Image** : `is_pdf_background_image` sur `res.company` — 66 748 chars base64 (~49 Ko)  
**Résultat** : ⚠️ **Partiellement fonctionnel** — même comportement que les tests précédents :
- Header : l'image de fond apparaît (le haut du papier-en-tête avec logo JES)
- Body : **PAS de fond visible** — le body reste blanc
- Footer : le bandeau vert du bas du papier-en-tête s'affiche, **mais en double** (bandeau vert superposé sur le contenu en bas du body + bandeau correct dans le footer réel)  

**Analyse** : L'hypothèse que "inline style fonctionne mais bloc `<style>` non" **est partiellement invalidée**. Le fond s'affiche dans le header et le footer (qui ont `subst=True` et sont rendus via wkhtmltopdf `--header-html` / `--footer-html`), mais **PAS dans le body**. Cela suggère que le problème n'est pas la méthode d'injection du CSS, mais plutôt que **wkhtmltopdf ne rend pas `background-image` dans le document body principal** quand l'image dépasse une certaine taille, ou que le body a un comportement de rendu différent.  
**Observation importante** : Le code natif Odoo met le `background-image` sur une `<div>` DANS le body (pas sur `<body>` lui-même). C'est peut-être une différence significative.

### Test 15 : `<div>` wrapper avec `background-image` + `position: absolute` dans body (comme le natif Odoo)

**Template** : héritage de `web.minimal_layout`  
**Méthode** : Au lieu de mettre le `background-image` sur `<body>`, on injecte une `<div>` avec `position: absolute; top: 0; left: 0; width: 210mm; height: 297mm; z-index: -1;` à l'intérieur du `<body>` via `<xpath expr="//body" position="inside">`. Le data URI est en inline `style=""` sur cette `<div>`, exactement comme Odoo le fait sur `.article`. Un JS dans `<head>` ajuste `background-position` selon la section.  
**Code** :
```xml
<xpath expr="//body" position="inside">
    <div t-if="is_bg_data" id="is_bg_div"
         t-attf-style="background-image: url({{ is_bg_data }}); background-size: 210mm 297mm;
         background-repeat: no-repeat; background-position: 0 0;
         -webkit-print-color-adjust: exact; print-color-adjust: exact;
         position: absolute; top: 0; left: 0; width: 210mm; height: 297mm; z-index: -1;"/>
</xpath>
```
**Résultat** : ❌ **Pire que le Test 14** :
- Header : le logo du papier-en-tête apparaît correctement en haut
- Body : le fond apparaît cette fois (on voit le logo JES en filigrane au centre), **MAIS** tout le contenu du rapport est décalé/masqué — seuls les montants à droite sont visibles, le reste du tableau est invisible (caché par la div ou décalé)
- Footer : le bandeau vert apparaît correctement
- Le contenu textuel du rapport (colonnes gauche du tableau) n'est plus visible

**Analyse** : La `<div>` en `position: absolute` avec `z-index: -1` se place visuellement derrière le contenu **en théorie**, mais dans le rendu wkhtmltopdf, elle semble perturber le flux du document. Le `z-index: -1` ne fonctionne pas correctement — la div se place DEVANT une partie du contenu (la partie gauche du tableau est cachée). Le fond est visible dans le body cette fois (contrairement au Test 14 où il ne l'était pas), ce qui confirme que mettre le data URI sur une `<div>` plutôt que sur `<body>` contourne le problème de taille.  
**Conclusion** : Le `background-image` data URI sur une `<div>` dans le body **FONCTIONNE** (le fond s'affiche). Mais le positionnement absolu avec `z-index: -1` ne met pas correctement la div derrière le contenu dans wkhtmltopdf.

---

## Ce qui a fonctionné

| Test | Méthode | Résultat |
|------|---------|----------|
| Test 4 | `background-color` simple dans `web.minimal_layout` `<head>` | ✅ Fond vert sur toutes les sections |
| Test 6 | `background-image` data URI 1px rouge dans `web.minimal_layout` | ✅ Fond rouge partout |
| Test 8 | `<img>` 200px dans body de `web.minimal_layout` | ✅ Image visible |

**Conclusions** :
- Le CSS dans `<head>` de `web.minimal_layout` **fonctionne**
- Les `background-color` simples **fonctionnent**
- Les très petites data URI en `background-image` **fonctionnent**
- Les `<img>` tags **fonctionnent** dans le body

---

## Ce qui n'a pas fonctionné du tout

| Test | Méthode | Raison |
|------|---------|--------|
| Tests 1-3 | Tout héritage de `web.report_layout` ou `web.external_layout_boxed` | `<head>` perdu par `_prepare_html()` |
| Tests 5, 7 | `background-image` data URI de plus de quelques octets | Limite wkhtmltopdf sur la taille des data URI en CSS |
| Test 11 | `position: fixed` dans le body | Non supporté par wkhtmltopdf dans le body (OK dans header/footer) |
| Test 12 | `background-image` via URL HTTP `/web/image/...` | URL non résolue ou bloquée par wkhtmltopdf |

---

## Ce qui a fonctionné partiellement

| Test | Méthode | Ce qui marche | Ce qui ne marche pas |
|------|---------|---------------|----------------------|
| Test 9 | `<img>` pleine page `position: absolute` dans body | Image visible dans le body | Ne couvre pas header/footer ; positionnement décalé |
| Test 10 | `<img>` dans header (`subst=True`) | Image s'affiche | Couvre le contenu (z-index inopérant entre documents séparés) |
| Test 13 | URL HTTP + JS positionnement | Footer OK, header montre l'image | Header dupliqué, body pas de fond |
| Test 14 | Inline `style=""` sur `<body>` + data URI + JS | Header OK, footer montre le bandeau vert | Body reste blanc ; footer en double (superposition) |
| Test 15 | `<div>` wrapper `position: absolute; z-index: -1` + data URI inline | Fond visible dans body + header + footer | Contenu du rapport masqué/décalé par la div (z-index -1 inefficace) |
| Test 16 | 3 images découpées + `<img>` `position: absolute` dans `minimal_layout` | Header et footer affichent l'image | Images pas pleine largeur (clippées par `overflow: hidden` de body `.container`) ; body pas de fond visible |
| Test 17 | Approche combinée : `background-image` body via JS + div article via héritage `external_layout_boxed` | — | Header/footer perdus ; body : image trop grosse, déborde sur 2 pages |

---

## Leçons clés

### Test 14
> Le **body principal** de wkhtmltopdf ne rend pas `background-image` sur `<body>` pour les images de taille significative. Header/footer l'affichent correctement.

### Test 15
> Mettre le data URI sur une **`<div>` dans le body** (comme le fait le code natif Odoo) **FONCTIONNE** — le fond s'affiche. C'est une avancée majeure.  
> Mais `position: absolute; z-index: -1` ne place pas correctement la div derrière le contenu dans wkhtmltopdf.

### Test 16
> `<img>` avec `position: absolute` dans `minimal_layout` est clippé par `overflow: hidden` sur `<body class="container overflow-hidden">`.

### Test 17 — Analyse détaillée

**Ce qui a été fait** :
- Template `external_layout_static_bg` (hérite `web.minimal_layout`) : data URIs header/footer dans `<input type="hidden">`, JS qui détecte la section et applique `background-image` sur `<body>`
- Template `external_layout_boxed_bg` (hérite `web.external_layout_boxed`) : `background-image` inline sur la div `.article` via `t-attf-style`

**Résultat observé** :
- Header et footer : **plus de contenu visible** — les sections header/footer ont perdu leur contenu (logo, adresse, bandeau vert…). Possiblement les images n'étaient pas uploadées dans les 3 champs découpés, OU le JS via `background-image` sur `<body>` ne fonctionne pas dans ce contexte
- Body : l'image s'affiche MAIS elle est **beaucoup trop grande** — le motif vert du papier-en-tête déborde largement et le rapport s'étend sur 2 pages

**Explications probables** :

1. **Header/footer disparus** : 
   - Il est possible que les champs `is_pdf_bg_header` et `is_pdf_bg_footer` n'aient pas été remplis (les images découpées n'ont pas été uploadées)
   - Le header/footer Odoo natif (logo, adresse) est produit par `web.external_layout_boxed` dans la div `.header` et `.footer`. Si le template `external_layout_boxed_bg` a cassé le rendu du layout boxed (mauvais xpath ou mauvais attribut), le header/footer natif peut avoir disparu aussi
   - **Problème probable** : l'attribut `t-attf-style` sur la div article a été **remplacé** (pas concaténé) par notre xpath. L'original contenait déjà un `t-attf-style` pour `layout_background_url`. Notre code le réécrit complètement. Si `layout_background_url` n'est pas défini dans le contexte de rendu de notre héritage, ça pourrait générer une erreur QWeb silencieuse qui casse tout le layout

2. **Body trop gros** :
   - `background-size: cover` fait que l'image couvre **tout** le conteneur `.article`. Si l'image uploadée est le morceau "body" (la partie centrale du papier-en-tête qui est surtout du blanc avec le motif vert), elle s'étire pour remplir la div article qui fait toute la hauteur du contenu
   - L'image du corps ne devrait pas être dimensionnée en `cover` mais plutôt en `contain` ou en taille fixe, SAUF si c'est une image qui fait exactement la taille attendue de la zone body
   - **Hypothèse** : l'utilisateur a peut-être uploadé l'image complète du papier-en-tête dans le champ body (pas une version découpée), ce qui donne un résultat surdimensionné

3. **Problème fondamental avec l'héritage de `external_layout_boxed`** :
   - On a supposé que l'inline style sur `.article` "survit" à `_prepare_html()`. C'est vrai pour le mécanisme natif car il met le style AVANT que `_prepare_html()` extraie la div. Notre héritage fait pareil (xpath ajoute le style au template, donc il est rendu avant extraction). Ça devrait fonctionner
   - MAIS : `_prepare_html()` extrait les div par class (`.header`, `.footer`, `.article`/`div.article`). Si le xpath a accidentellement changé la structure de la div (en plus de l'attribut), ça pourrait casser l'extraction

**Correction après retour utilisateur** : les images étaient bien uploadées dans les 3 champs. Le header et le footer Odoo natifs étaient visibles avant cette modification. L'explication réelle : **l'image du body est devenue énorme** à cause de `background-size: cover` et vient **par-dessus** les images du header et du footer, les cachant. Le `cover` étire l'image proportionnellement pour couvrir toute la div `.article`, et comme le ratio hauteur/largeur de l'image body (conçue pour ~213mm de haut sur 210mm de large) est forcé à couvrir la div, elle s'étend bien au-delà de la zone body, recouvrant visuellement le header et le footer.

**Leçon** : `background-size: cover` est inadapté ici. Il faudrait `background-size: 100% auto` ou `contain`, et éviter que l'image ne dépasse sa zone.

---

## Pistes non explorées

### Piste 1 : Utiliser le mécanisme natif `layout_background`

Odoo 18 possède nativement les champs `layout_background` et `layout_background_image` sur `res.company`. La configuration se fait via **Paramètres → Mise en page du document** :
- Mettre `layout_background` = "Custom"
- Uploader l'image dans `layout_background_image`

**Avantage** : le code natif applique le fond en data URI directement en style inline sur la `<div>` article, ce qui fonctionne.  
**Limitation** : ne couvre que la zone body (entre header et footer), pas toute la page.  
**À tester** : vérifier si ça suffit visuellement, quitte à ajuster les marges.

### Piste 2 : 3 images séparées (header, body, footer)

Découper l'image du papier-en-tête en 3 morceaux :
- **Image header** : les 52mm du haut (logo + coordonnées)
- **Image body** : la zone centrale (filigrane/fond)
- **Image footer** : les 32mm du bas (bandeau vert)

Injecter chaque morceau dans la section correspondante via `<img>` avec `position: absolute`. On sait que `<img>` fonctionne (Test 8).

**Avantage** : contourne le problème des 3 documents HTML séparés.  
**Difficulté** : taille et synchronisation des morceaux avec les marges.

### Piste 3 : Surcharger `_build_wkhtmltopdf_args()` pour activer `--enable-local-file-access`

```python
class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'
    
    def _build_wkhtmltopdf_args(self, paperformat_id, landscape, specific_paperformat_args=None, set_viewport_size=False):
        args = super()._build_wkhtmltopdf_args(...)
        # Remplacer --disable-local-file-access par --enable-local-file-access
        args = [a for a in args if a != '--disable-local-file-access']
        args.insert(0, '--enable-local-file-access')
        return args
```

Cela permettrait d'utiliser des `file://` URLs ou de lever d'autres restrictions.  
**Risque sécurité** : à évaluer — en environnement interne, le risque est faible.

### Piste 4 : Injecter le base64 directement en inline style `<img src="data:...">`

On sait que `<img>` fonctionne (Test 8) et que le mécanisme natif utilise `data:image/png;base64,...` en inline style (et ça marche). L'idée :

```xml
<img t-att-src="image_data_uri(env.company.is_pdf_background_image)"
     style="position: absolute; top: 0; left: 0; width: 210mm; height: 297mm; z-index: -1;"/>
```

Cela a été tenté (Test 9) avec un résultat partiel. La différence avec le mécanisme natif : le natif met le data URI sur un `background-image` d'un `<div>` (inline style), pas sur un `<img>`.

**À re-tester** avec :
- `background-image` en style inline sur un `<div>` wrapper (comme le fait le code natif)
- Taille d'image réduite (le natif ne limite pas la taille, donc ça devrait marcher)

### Piste 5 : Combiner le mécanisme natif avec des ajustements CSS

Utiliser `layout_background_image` natif pour le body, puis ajouter des `<img>` séparés pour header et footer uniquement, via héritage de `web.minimal_layout` avec condition sur `subst`.

### Piste 6 : background-image en inline style sur `<body>` (pas en `<style>`)

Le mécanisme natif met le background-image en **attribut style inline** sur la div, pas dans un `<style>` dans `<head>`. Peut-être que wkhtmltopdf traite différemment les data URI en inline style vs en feuille de style.

```xml
<xpath expr="//body" position="attributes">
    <attribute name="style">
        background-image: url(data:image/png;base64,...) !important;
        background-size: 210mm 297mm;
    </attribute>
</xpath>
```

### Piste 7 : Utiliser `@page` CSS pour le fond

```css
@page {
    background-image: url(data:image/png;base64,...);
    background-size: 210mm 297mm;
}
```

Peu probable que wkhtmltopdf supporte `@page background-image`, mais non testé.

---

## Fichiers impliqués

### Fichiers du module

| Fichier | Rôle |
|---------|------|
| `report/report_layout.xml` | Template QWeb héritant de `web.minimal_layout` — le fichier principal modifié |
| `models/res_company.py` | Définit `is_pdf_background_image = fields.Binary(attachment=True)` |
| `views/res_company_view.xml` | Vue pour uploader l'image dans la fiche société |
| `static/src/img/papier-en-tete-jes.jpg` | Image test réduite (6.6 Ko) |
| `static/src/img/papier-en-tete-jes.png` | Image test réduite PNG (11 Ko) |
| `__manifest__.py` | Inclut `report/report_layout.xml` dans `data` |

### Fichiers Odoo de référence

| Fichier | Contenu pertinent |
|---------|-------------------|
| `0-odoo18/addons/web/views/report_templates.xml` | Templates `web.minimal_layout`, `web.external_layout_boxed`, etc. — ~993 lignes |
| `0-odoo18/odoo/addons/base/models/ir_actions_report.py` | `_prepare_html()`, `_build_wkhtmltopdf_args()`, `_run_wkhtmltopdf()` |
| `0-odoo18/odoo/addons/base/models/res_company.py` | Champs natifs `layout_background`, `layout_background_image` |
| `0-odoo18/addons/web/models/base_document_layout.py` | Vue de configuration du document layout |
| `0-odoo18/addons/web/static/src/webclient/actions/reports/report.scss` | CSS `.o_report_layout_background` |

---

## Configuration actuelle

### Template actuel (`report/report_layout.xml`)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="external_layout_static_bg" inherit_id="web.minimal_layout">
        <xpath expr="//head" position="inside">
            <t t-set="is_bg_company" t-value="env.company"/>
            <t t-if="'is_pdf_background_image' in is_bg_company._fields and is_bg_company.is_pdf_background_image">
                <t t-set="is_bg_url" t-value="'/web/image/res.company/%s/is_pdf_background_image' % is_bg_company.id"/>
                <t t-set="is_pf" t-value="env['ir.actions.report'].get_paperformat_by_xmlid(report_xml_id) if report_xml_id else None"/>
                <t t-set="is_mt" t-value="int(is_pf.margin_top) if is_pf else 40"/>
                <t t-set="is_mb" t-value="int(is_pf.margin_bottom) if is_pf else 20"/>
                <style>
                    body {
                        <t t-out="'background-image: url(%s) !important;' % is_bg_url"/>
                        background-size: 210mm 297mm !important;
                        background-repeat: no-repeat !important;
                        background-position: 0 0 !important;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }
                </style>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        var mt = <t t-out="is_mt"/>;
                        var mb = <t t-out="is_mb"/>;
                        if (document.getElementById('minimal_layout_report_headers')) {
                            document.body.style.backgroundPosition = '0 0';
                        } else if (document.getElementById('minimal_layout_report_footers')) {
                            document.body.style.backgroundPosition = '0 -' + (297 - mb) + 'mm';
                        } else {
                            document.body.style.backgroundPosition = '0 -' + mt + 'mm';
                        }
                    });
                </script>
            </t>
        </xpath>
    </template>
</odoo>
```

### Champ modèle (`models/res_company.py`)

```python
is_pdf_background_image = fields.Binary(
    string="Image de fond PDF",
    attachment=True,
)
```

### ID en base de données

- Vue `external_layout_static_bg` : **id=1663** (hérite de view 199 = `web.minimal_layout`)

### Pour mettre à jour après modification

```bash
ssh odoo@bookworm
sudo systemctl restart odoo-jura-energie-solaire18
# ou avec -u pour forcer la mise à jour du module :
# passer par l'interface Odoo : Apps → Mettre à jour le module
```

---

## Résumé des contraintes wkhtmltopdf

1. **3 documents HTML séparés** — header, body, footer rendus indépendamment
2. **`--disable-local-file-access`** — pas de `file://` 
3. **`position: fixed` ne fonctionne pas dans le body** — seulement dans header/footer
4. **Data URI en CSS `background-image` : limite de taille** — fonctionne pour 1px, échoue pour ~11 Ko+ 
5. **Data URI en attribut `src` de `<img>` : fonctionne** — même pour des images de taille raisonnable
6. **Data URI en inline `style` sur un `<div>` : fonctionne** — c'est ce que fait le code natif Odoo
7. **URL HTTP `/web/image/...`** : statut incertain — devrait fonctionner via cookie jar, mais résultat non concluant
8. **JavaScript fonctionne** — via `--javascript-delay 1000`, le JS a le temps de s'exécuter
9. **`-webkit-print-color-adjust: exact`** : nécessaire pour que les couleurs/images s'impriment

---

## Conclusion et prochaine étape

Après 15 tests, on se heurte à **deux problèmes impossibles à résoudre simultanément** avec wkhtmltopdf :

1. **Le fond sur `<body>` ne s'affiche pas** dans le document principal pour les images de taille significative (Tests 5, 7, 14)
2. **Le fond sur une `<div>` dans le body s'affiche** (Test 15, mécanisme natif Odoo) mais **ne couvre que la zone body** — pas le header ni le footer
3. **Header et footer sont des documents HTML séparés** → impossible d'avoir un seul élément HTML/CSS couvrant les 3 zones

Le mécanisme natif Odoo (`layout_background` / `layout_background_image`) a exactement la même limitation : il ne couvre que la div `.article` (zone body).

### Piste prioritaire pour la prochaine session : 3 images découpées

La seule approche non testée qui contourne réellement l'architecture 3-documents-séparés de wkhtmltopdf est la **Piste 2** : **découper le papier-en-tête en 3 morceaux** :

- **Image header** (52mm du haut) : logo JES + coordonnées → injectée dans le header via `<img>` dans `minimal_layout` quand `subst=True` et `#minimal_layout_report_headers` est présent
- **Image body** (zone centrale 213mm) : fond blanc ou filigrane discret → injectée dans le body via le mécanisme natif `layout_background` ou une `<div>` avec `background-image`
- **Image footer** (32mm du bas) : bandeau vert + coordonnées → injectée dans le footer via `<img>` dans `minimal_layout` quand `subst=True` et `#minimal_layout_report_footers` est présent

On sait que `<img>` fonctionne dans toutes les sections (Test 8), et que `background-image` sur une `<div>` fonctionne dans le body (Test 15). Il faudra :
1. Découper l'image source en 3 avec les bonnes dimensions
2. Stocker les 3 morceaux (soit en champs Binary, soit en fichiers statiques)
3. Injecter chaque morceau dans sa section avec le bon positionnement

### Test 16 : Implémentation de la Piste 2 — 3 images découpées (en cours)

**Modifications effectuées** :

#### 3 nouveaux champs sur `res.company` (`models/res_company.py`)
```python
is_pdf_bg_header = fields.Binary(string="Fond PDF - En-tête", attachment=True)
is_pdf_bg_body   = fields.Binary(string="Fond PDF - Corps", attachment=True)
is_pdf_bg_footer = fields.Binary(string="Fond PDF - Pied de page", attachment=True)
```

#### Vue mise à jour (`views/res_company_view.xml`)
Un nouveau groupe "Fond PDF découpé" avec les 3 champs image à uploader.

#### Nouveau template (`report/report_layout.xml`)
```xml
<template id="external_layout_static_bg" inherit_id="web.minimal_layout">
    <xpath expr="//head">
        <!-- Prépare les 3 data URIs via image_data_uri() -->
        <!-- Images header/footer cachées par défaut via CSS display:none -->
        <!-- JS DOMContentLoaded détecte #minimal_layout_report_headers ou 
             #minimal_layout_report_footers et affiche la bonne image -->
    </xpath>
    <xpath expr="//body" position="inside">
        <!-- Header : <img> position:absolute (affiché par JS si section header) -->
        <!-- Footer : <img> position:absolute (affiché par JS si section footer) -->
        <!-- Body : <div> avec background-image inline style (pas de JS nécessaire) -->
    </xpath>
</template>
```

**Principe** :
- `subst=True` → on est dans header OU footer → les 2 `<img>` sont injectés mais cachés (`display: none`)
- JS détecte `#minimal_layout_report_headers` → affiche l'image header
- JS détecte `#minimal_layout_report_footers` → affiche l'image footer
- `not subst` → on est dans le body → une `<div>` avec `background-image` inline (technique du Test 15)

**Pour tester** :
1. Mettre à jour le module (`-u is_jura_energie_solaire_18`)
2. Aller dans Société → onglet JES → groupe "Fond PDF découpé"
3. Uploader les 3 morceaux d'image découpés
4. Imprimer un rapport PDF

---

## Approche finale : Fusion Python PyPDF2 (post-génération)

> **Date** : 11 avril 2026
> **Statut** : ✅ Implémentée

### Principe

Abandon de l'injection CSS/HTML dans wkhtmltopdf. Nouvelle stratégie :
1. Générer le PDF Odoo normalement (sans fond)
2. Fusionner chaque page avec un PDF de fond (papier-en-tête) via **PyPDF2**
3. Retourner le PDF fusionné en téléchargement

### Avantages
- Contourne toutes les limitations de wkhtmltopdf (3 documents HTML séparés, data URI tronquées, etc.)
- Fonctionne avec n'importe quel rapport Odoo
- Le fond est un PDF d'une page → qualité parfaite, pas de conversion d'image

### Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `models/res_company.py` | Ajout champ `is_pdf_background` (Binary, attachment) pour stocker le PDF de fond |
| `views/res_company_view.xml` | Ajout du champ dans l'onglet JES → groupe PDF |
| `models/purchase_order.py` | Méthode `action_print_pdf_with_background()` : génère le PDF, fusionne avec le fond, crée une pièce jointe et retourne l'URL de téléchargement |
| `views/purchase_order_view.xml` | Bouton "Imprimer avec papier-en-tête" dans le header (visible en état `purchase`/`done`) |

### Configuration

1. Mettre à jour le module (`-u is_jura_energie_solaire_18`)
2. Aller dans **Société → onglet JES → groupe PDF**
3. Uploader un **PDF d'une page** contenant le papier-en-tête (fond)
4. Ouvrir un bon de commande confirmé → cliquer sur **"Imprimer avec papier-en-tête"**

### Code clé (`purchase_order.py`)

```python
def action_print_pdf_with_background(self):
    # 1. Générer le PDF standard via le rapport Odoo
    report = self.env.ref('purchase.action_report_purchase_order')
    pdf_content, _ = report._render_qweb_pdf(report.id, [self.id])

    # 2. Lire le PDF de fond (une page)
    bg_reader = PdfReader(io.BytesIO(base64.b64decode(bg_pdf_data)))
    bg_page = bg_reader.pages[0]

    # 3. Pour chaque page du contenu, copier le fond et fusionner
    for page in content_reader.pages:
        bg_copy = copy(bg_page)       # copie indépendante du fond
        bg_copy.merge_page(page)       # contenu PAR-DESSUS le fond
        writer.add_page(bg_copy)

    # 4. Créer pièce jointe + retourner URL téléchargement
```
