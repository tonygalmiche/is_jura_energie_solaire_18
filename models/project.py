# -*- coding: utf-8 -*-
from odoo import fields, models, api  


class project_project(models.Model):
    _inherit = "project.project"

    is_date_contact      = fields.Date('Date contact', tracking=True)
    is_das               = fields.Char('DAS', size=17, tracking=True)
    is_origine           = fields.Char('Origine', size=40, tracking=True)
    is_charge_affaire_id = fields.Many2one('res.partner', 'Chargé d\'Affaire', tracking=True)
    is_date_devis        = fields.Date('Date devis', tracking=True)
    is_montant           = fields.Monetary('Montant', currency_field='currency_id', tracking=True)
    is_taux_chance       = fields.Float('Taux de chance (%)', digits=(3, 2), tracking=True)
    is_date_decision     = fields.Date('Date décision', tracking=True)
    is_potentiel         = fields.Monetary('Potentiel', currency_field='currency_id', tracking=True)
    is_informations      = fields.Text('Informations', tracking=True)
    is_version           = fields.Integer('Version', tracking=True)
