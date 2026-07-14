-- Corrige les pièces jointes de is.centrale dont le res_id est incohérent
-- avec le lien réel stocké dans les tables de relation many2many.
--
-- Contexte : Odoo calcule les droits d'accès à ir.attachment à partir des
-- champs res_model/res_id (cf. addons/base/models/ir_attachment.py, méthode
-- check()) et non à partir des tables de relation many2many. Si res_id vaut 0
-- (ou pointe vers un mauvais enregistrement), seul le créateur de la pièce
-- jointe (create_uid) ou un administrateur peut la lire, même si
-- l'utilisateur a normalement accès à la centrale liée.
--
-- Cas identifiés au moment de l'écriture de ce script :
--   - ir_attachment.id = 1814 (res_id = 0, devrait être 3145)
--   - ir_attachment.id = 3444 (res_id = 0, devrait être 3236)
--
-- Cette requête est générique : elle balaie toutes les tables de relation
-- documentaires de is.centrale et ne modifie que les lignes où le res_id
-- actuel ne correspond à AUCUNE des centrales réellement liées (donc les
-- pièces jointes déjà correctement partagées entre plusieurs centrales ne
-- sont pas touchées).

-- 1) Vérification (à exécuter avant toute modification)
SELECT 'is_centrale_pv_attachment_rel' tbl, a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_pv_attachment_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_contrat_signe_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_contrat_signe_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_dp_attachment_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_dp_attachment_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_crd_signe_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_crd_signe_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_cardi_signe_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_cardi_signe_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_socotec_conformite_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_socotec_conformite_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_consuel_attachment_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_consuel_attachment_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_s21_attestation_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_s21_attestation_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_plan_calepinage_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_plan_calepinage_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_plan_chaines_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_plan_chaines_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_plan_dimensionnement_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_plan_dimensionnement_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_plan_raccordement_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_plan_raccordement_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_plan_schema_unifilaire_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_plan_schema_unifilaire_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_plan_securite_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_plan_securite_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_plan_masse_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_plan_masse_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_plan_note_calculs_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_plan_note_calculs_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
UNION ALL
SELECT 'is_centrale_plan_autres_rel', a.id, a.res_id, sub.new_res_id FROM ir_attachment a JOIN (SELECT attachment_id, MIN(centrale_id) new_res_id, array_agg(centrale_id) all_ids FROM is_centrale_plan_autres_rel GROUP BY attachment_id) sub ON sub.attachment_id=a.id WHERE a.res_model='is.centrale' AND NOT (a.res_id = ANY(sub.all_ids))
;

-- 2) Correction (à exécuter uniquement après avoir validé le résultat ci-dessus)
-- Conseil : englober dans BEGIN; ... COMMIT; / ROLLBACK; pour pouvoir annuler.
--
DO $$
DECLARE
    rel_table text;
    rel_tables text[] := ARRAY[
        'is_centrale_pv_attachment_rel',
        'is_centrale_contrat_signe_rel',
        'is_centrale_dp_attachment_rel',
        'is_centrale_crd_signe_rel',
        'is_centrale_cardi_signe_rel',
        'is_centrale_socotec_conformite_rel',
        'is_centrale_consuel_attachment_rel',
        'is_centrale_s21_attestation_rel',
        'is_centrale_plan_calepinage_rel',
        'is_centrale_plan_chaines_rel',
        'is_centrale_plan_dimensionnement_rel',
        'is_centrale_plan_raccordement_rel',
        'is_centrale_plan_schema_unifilaire_rel',
        'is_centrale_plan_securite_rel',
        'is_centrale_plan_masse_rel',
        'is_centrale_plan_note_calculs_rel',
        'is_centrale_plan_autres_rel'
    ];
BEGIN
    FOREACH rel_table IN ARRAY rel_tables LOOP
        EXECUTE format(
            'UPDATE ir_attachment a
             SET res_id = sub.new_res_id
             FROM (
               SELECT attachment_id, MIN(centrale_id) AS new_res_id, array_agg(centrale_id) AS all_ids
               FROM %I
               GROUP BY attachment_id
             ) sub
             WHERE sub.attachment_id = a.id
               AND a.res_model = ''is.centrale''
               AND NOT (a.res_id = ANY(sub.all_ids))',
            rel_table
        );
    END LOOP;
END $$;
