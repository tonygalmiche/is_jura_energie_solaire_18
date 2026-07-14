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
