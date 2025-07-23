# -*- coding: utf-8 -*-
from odoo import fields, models, api  

class crm_lead(models.Model):
    _inherit = "crm.lead"
    
    is_secteur = fields.Selection(
        [
            ('gp', 'GP'),
            ('re', 'RE'),
            ('th', 'TH'),
            ('si', 'SI'),
        ],
        string="Secteur",
        tracking=True,
    )
    is_adresse      = fields.Char("Adresse", size=60, tracking=True)
    is_localisation = fields.Char("Localisation", tracking=True)
