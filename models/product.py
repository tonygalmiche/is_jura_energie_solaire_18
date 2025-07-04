# -*- coding: utf-8 -*-
from odoo import fields, models, api  


class IsFamille(models.Model):
    _name='is.famille'
    _description = "Famille"
    _order='name'

    name = fields.Char('Famille', required=True, index=True)


class product_template(models.Model):
    _inherit = "product.template"
    _order="name"

    is_famille_id    = fields.Many2one('is.famille', 'Famille', tracking=True)
    is_reference     = fields.Char('Référence', tracking=True)
    is_marque        = fields.Char('Marque', tracking=True)
    is_puissance_kva = fields.Integer('Puissance (kVA)', tracking=True, help="Pour les onduleurs")
    is_puissance_w   = fields.Integer('Puissance (W)'  , tracking=True, help="Pour les panneaux")
