# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IsUserGroupMatrix(models.Model):
    _name = 'is.user.group.matrix'
    _description = 'Matrice Utilisateurs / Groupes'
    _auto = False
    _order = 'user_id, group_full_name'

    user_id = fields.Many2one('res.users', string='Utilisateur', readonly=True)
    group_id = fields.Many2one('res.groups', string='Groupe', readonly=True)
    group_full_name = fields.Char(string='Groupe', readonly=True)
    category_id = fields.Many2one('ir.module.category', string='Catégorie', readonly=True)
    count = fields.Integer(string='Présent', readonly=True, default=1)

    def init(self):
        """Crée la vue SQL pour la matrice utilisateurs/groupes"""
        self.env.cr.execute("""
            DROP VIEW IF EXISTS is_user_group_matrix;
            CREATE OR REPLACE VIEW is_user_group_matrix AS (
                SELECT
                    ROW_NUMBER() OVER () as id,
                    u.id as user_id,
                    g.id as group_id,
                    COALESCE(c.name->>'fr_FR', c.name->>'en_US', '') || ' / ' || COALESCE(g.name->>'fr_FR', g.name->>'en_US', '') as group_full_name,
                    COALESCE(c.parent_id, c.id) as category_id,
                    1 as count
                FROM res_users u
                JOIN res_groups_users_rel rel ON rel.uid = u.id
                JOIN res_groups g ON g.id = rel.gid
                LEFT JOIN ir_module_category c ON c.id = g.category_id
                LEFT JOIN ir_module_category cp ON cp.id = c.parent_id
                WHERE u.active = true
                  AND u.share = false
                  AND u.id NOT IN (1, 2)
                  AND c.id IS NOT NULL
                  AND c.visible = true
                  AND c.parent_id IS NOT NULL
                ORDER BY u.id, group_full_name
            )
        """)

    def action_open_user(self):
        """Ouvre le formulaire complet de l'utilisateur avec les droits d'accès"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Utilisateur',
            'res_model': 'res.users',
            'res_id': self.user_id.id,
            'view_mode': 'form',
            'view_id': self.env.ref('base.view_users_form').id,
            'target': 'current',
            'context': {'show_user_group_warning': True},
        }
