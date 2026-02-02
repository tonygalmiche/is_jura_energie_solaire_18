# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IsFormeJuridique(models.Model):
    _name = 'is.forme.juridique'
    _description = 'Forme juridique'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_client_a_risque = fields.Selection(
        [
            ('oui', 'Oui'),
            ('non', 'Non'),
        ],
        string="Client à risque",
        tracking=True,
        default='non'
    )
    is_centrale_ids = fields.One2many('is.centrale', 'client_id', string="Centrales")
    is_forme_juridique_id = fields.Many2one('is.forme.juridique', string="Forme juridique")
    is_capital_social = fields.Float(string="Capital social (€)")
    is_lieu_rcs = fields.Char(string="Lieu d'immatriculation RCS")
    is_code_naf = fields.Char(string="Code NAF")

    def action_open_contact(self):
        """Ouvrir la fiche du contact"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
