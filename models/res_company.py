# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_conditions_generales_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='is_company_conditions_generales_rel',
        column1='company_id',
        column2='attachment_id',
        string="Conditions générales",
    )
