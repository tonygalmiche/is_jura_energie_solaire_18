# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IsUserGroupMatrix(models.Model):
    _name = 'is.user.group.matrix'
    _description = 'Matrice Utilisateurs / Groupes'
    _auto = False
    _order = 'user_name, group_name'

    user_id = fields.Many2one('res.users', string='Utilisateur', readonly=True)
    user_name = fields.Char(string='Utilisateur', readonly=True)
    group_id = fields.Many2one('res.groups', string='Groupe', readonly=True)
    group_name = fields.Char(string='Groupe', readonly=True)
    category_id = fields.Many2one('ir.module.category', string='Catégorie', readonly=True)
    category_name = fields.Char(string='Catégorie', readonly=True)
    count = fields.Integer(string='Présent', readonly=True, default=1)

    def init(self):
        """Crée la vue SQL pour la matrice utilisateurs/groupes"""
        self.env.cr.execute("""
            DROP VIEW IF EXISTS is_user_group_matrix;
            CREATE OR REPLACE VIEW is_user_group_matrix AS (
                SELECT
                    ROW_NUMBER() OVER () as id,
                    u.id as user_id,
                    u.login as user_name,
                    g.id as group_id,
                    g.name as group_name,
                    c.id as category_id,
                    COALESCE(cp.name, c.name) as category_name,
                    1 as count
                FROM res_users u
                JOIN res_groups_users_rel rel ON rel.uid = u.id
                JOIN res_groups g ON g.id = rel.gid
                LEFT JOIN ir_module_category c ON c.id = g.category_id
                LEFT JOIN ir_module_category cp ON cp.id = c.parent_id
                WHERE u.active = true
                  AND u.share = false
                  AND c.id IS NOT NULL
                  AND c.visible = true
                  AND (c.parent_id IS NOT NULL OR c.id NOT IN (
                      SELECT id FROM ir_module_category 
                      WHERE name IN ('Technical', 'Hidden', 'Extra Rights', 'Other Extra Rights', 'User types')
                  ))
                ORDER BY u.login, c.sequence, g.name
            )
        """)

    def action_open_user(self):
        """Ouvre le formulaire de l'utilisateur"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Utilisateur',
            'res_model': 'res.users',
            'res_id': self.user_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_group(self):
        """Ouvre le formulaire du groupe"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Groupe',
            'res_model': 'res.groups',
            'res_id': self.group_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
