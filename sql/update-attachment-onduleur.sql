-- Corrige les pièces jointes de is.centrale.onduleur (garanties) dont le
-- res_id est incohérent avec le lien réel stocké dans la table de relation
-- many2many is_centrale_onduleur_garantie_rel.
--
-- Contexte : Odoo calcule les droits d'accès à ir.attachment à partir des
-- champs res_model/res_id (cf. addons/base/models/ir_attachment.py, méthode
-- check()) et non à partir des tables de relation many2many. Si res_id vaut 0
-- (ou pointe vers un mauvais enregistrement), seul le créateur de la pièce
-- jointe (create_uid) ou un administrateur peut la lire, même si
-- l'utilisateur a normalement accès à l'onduleur lié.
--
-- Cas identifiés au moment de l'écriture de ce script (res_id = 0) :
--   - ir_attachment.id = 726, 727, 788, 789

-- 1) Vérification (à exécuter avant toute modification)
SELECT a.id, a.res_id, a.res_model, sub.new_res_id, sub.all_ids
FROM ir_attachment a
JOIN (
    SELECT attachment_id, MIN(onduleur_id) AS new_res_id, array_agg(onduleur_id) AS all_ids
    FROM is_centrale_onduleur_garantie_rel
    GROUP BY attachment_id
) sub ON sub.attachment_id = a.id
WHERE a.res_model = 'is.centrale.onduleur'
  AND NOT (a.res_id = ANY(sub.all_ids));

-- 2) Correction (à exécuter uniquement après avoir validé le résultat ci-dessus)
-- Conseil : englober dans BEGIN; ... COMMIT; / ROLLBACK; pour pouvoir annuler.
--
UPDATE ir_attachment a
SET res_id = sub.new_res_id
FROM (
    SELECT attachment_id, MIN(onduleur_id) AS new_res_id, array_agg(onduleur_id) AS all_ids
    FROM is_centrale_onduleur_garantie_rel
    GROUP BY attachment_id
) sub
WHERE sub.attachment_id = a.id
  AND a.res_model = 'is.centrale.onduleur'
  AND NOT (a.res_id = ANY(sub.all_ids));
