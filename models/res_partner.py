# -*- coding: utf-8 -*-
from odoo import api, fields, models


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
