-- Corrige les pièces jointes produit (fiche technique / certification /
-- notice) dont res_model et/ou res_id sont incohérents avec le lien réel
-- stocké dans les tables de relation many2many.
--
-- Contexte : Odoo calcule les droits d'accès à ir.attachment à partir des
-- champs res_model/res_id (cf. addons/base/models/ir_attachment.py, méthode
-- check()). Les champs is_fiche_technique_ids / is_certification_ids /
-- is_notice_ids sont déclarés sur product.template (voir
-- is_jura_energie_solaire_18/models/product.py), avec les tables de relation
-- product_template_is_fiche_technique_rel / ..._certification_rel /
-- ..._notice_rel (colonne product_id = id produit template).
--
-- Cas identifié au moment de l'écriture de ce script :
--   - ir_attachment.id = 3679 : res_model = 'product.product', res_id = 0,
--     alors que la relation product_template_is_fiche_technique_rel indique
--     product_id = 360. Il faut donc corriger res_model ET res_id.
--
-- Investigation (voir historique de conversation) : en vérifiant les 3 tables
-- de relation, 8 attachements sur 11 avaient res_model = 'product.product' au
-- lieu de 'product.template'. Le code JS d'Odoo (many2many_binary_field.xml,
-- FileInput resModel="props.record.resModel") fixe toujours le res_model de
-- l'upload sur le modèle du formulaire affiché au moment de l'ajout du
-- fichier — ce n'est pas un tirage aléatoire ni un bug d'Odoo. Or ces 3
-- champs ne sont exposés, dans tout le code actuel de ce module, que sur la
-- vue product.template (views/product_view.xml) : avec le code actuel, un
-- upload via ce widget produit donc toujours res_model='product.template'.
-- Comme il n'y a eu ni import de données ni modification récente du code,
-- l'hypothèse la plus cohérente est que ces champs étaient auparavant
-- déclarés/affichés sur product.product (avant migration vers
-- product.template), et que les anciens attachements n'ont pas été migrés en
-- même temps. Non vérifiable formellement : ce dossier n'est pas un dépôt git
-- (pas d'historique disponible). Dans tous les cas, le correctif ci-dessous
-- réaligne ces données sur l'état actuel du code (product.template).



-- Anomalies identifiées le 14/07/2026 et non corrigées pour voir 
-- si le problème s'agrave
--         src         |  id  | res_id |    res_model     | new_res_id | all_ids 
-- --------------------+------+--------+------------------+------------+---------
--  is_fiche_technique | 2087 |    239 | product.template |        240 | {240}
--  is_fiche_technique | 3824 |     38 | product.product  |         38 | {38}
--  is_fiche_technique | 3346 |     10 | product.product  |         10 | {10}
--  is_fiche_technique | 3997 |     22 | product.product  |         22 | {22}
--  is_fiche_technique | 3679 |      0 | product.product  |        360 | {360}
--  is_certification   | 2088 |    239 | product.template |        240 | {240}
--  is_certification   | 3825 |     38 | product.product  |         38 | {38}
--  is_certification   | 3827 |    207 | product.product  |        207 | {207}
--  is_certification   | 3998 |     22 | product.product  |         22 | {22}
--  is_notice          | 2089 |    239 | product.template |        240 | {240}
--  is_notice          | 3826 |    207 | product.product  |        207 | {207}
-- (11 lignes)




-- 1) Vérification (à exécuter avant toute modification)
SELECT 'is_fiche_technique' src, a.id, a.res_id, a.res_model, sub.new_res_id, sub.all_ids
FROM ir_attachment a
JOIN (
    SELECT attachment_id, MIN(product_id) AS new_res_id, array_agg(product_id) AS all_ids
    FROM product_template_is_fiche_technique_rel
    GROUP BY attachment_id
) sub ON sub.attachment_id = a.id
WHERE (a.res_model != 'product.template' OR NOT (a.res_id = ANY(sub.all_ids)))
UNION ALL
SELECT 'is_certification', a.id, a.res_id, a.res_model, sub.new_res_id, sub.all_ids
FROM ir_attachment a
JOIN (
    SELECT attachment_id, MIN(product_id) AS new_res_id, array_agg(product_id) AS all_ids
    FROM product_template_is_certification_rel
    GROUP BY attachment_id
) sub ON sub.attachment_id = a.id
WHERE (a.res_model != 'product.template' OR NOT (a.res_id = ANY(sub.all_ids)))
UNION ALL
SELECT 'is_notice', a.id, a.res_id, a.res_model, sub.new_res_id, sub.all_ids
FROM ir_attachment a
JOIN (
    SELECT attachment_id, MIN(product_id) AS new_res_id, array_agg(product_id) AS all_ids
    FROM product_template_is_notice_rel
    GROUP BY attachment_id
) sub ON sub.attachment_id = a.id
WHERE (a.res_model != 'product.template' OR NOT (a.res_id = ANY(sub.all_ids)))
;

-- 2) Correction (à exécuter uniquement après avoir validé le résultat ci-dessus)
-- Conseil : englober dans BEGIN; ... COMMIT; / ROLLBACK; pour pouvoir annuler.
-- Corrige à la fois res_model (-> 'product.template') et res_id.
--
-- UPDATE ir_attachment a
-- SET res_model = 'product.template',
--     res_id = sub.new_res_id
-- FROM (
--     SELECT attachment_id, MIN(product_id) AS new_res_id, array_agg(product_id) AS all_ids
--     FROM product_template_is_fiche_technique_rel
--     GROUP BY attachment_id
-- ) sub
-- WHERE sub.attachment_id = a.id
--   AND (a.res_model != 'product.template' OR NOT (a.res_id = ANY(sub.all_ids)));
--
-- UPDATE ir_attachment a
-- SET res_model = 'product.template',
--     res_id = sub.new_res_id
-- FROM (
--     SELECT attachment_id, MIN(product_id) AS new_res_id, array_agg(product_id) AS all_ids
--     FROM product_template_is_certification_rel
--     GROUP BY attachment_id
-- ) sub
-- WHERE sub.attachment_id = a.id
--   AND (a.res_model != 'product.template' OR NOT (a.res_id = ANY(sub.all_ids)));
--
-- UPDATE ir_attachment a
-- SET res_model = 'product.template',
--     res_id = sub.new_res_id
-- FROM (
--     SELECT attachment_id, MIN(product_id) AS new_res_id, array_agg(product_id) AS all_ids
--     FROM product_template_is_notice_rel
--     GROUP BY attachment_id
-- ) sub
-- WHERE sub.attachment_id = a.id
--   AND (a.res_model != 'product.template' OR NOT (a.res_id = ANY(sub.all_ids)));
