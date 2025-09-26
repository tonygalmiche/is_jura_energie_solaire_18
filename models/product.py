# -*- coding: utf-8 -*-
from odoo import fields, models, api  


class IsFamille(models.Model):
    _name='is.famille'
    _description = "Famille"
    _order='name'

    name = fields.Char('Famille', required=True, index=True)
    parent_id = fields.Many2one('is.famille', 'Famille parent', ondelete='cascade')
    sous_famille_ids = fields.One2many('is.famille', 'parent_id', 'Sous-familles')


class product_template(models.Model):
    _inherit = "product.template"
    _order="name"

    is_famille_id      = fields.Many2one('is.famille', 'Famille', tracking=True, domain="[('parent_id', '=', False)]")
    is_sous_famille_id = fields.Many2one('is.famille', 'Sous-famille', tracking=True)
    is_reference       = fields.Char('Référence', tracking=True)
    is_marque          = fields.Char('Marque', tracking=True)
    is_puissance_kva   = fields.Integer('Puissance (kVA)', tracking=True, help="Pour les onduleurs")
    is_puissance_w     = fields.Integer('Puissance (W)'  , tracking=True, help="Pour les panneaux")

    @api.onchange('is_famille_id')
    def _onchange_is_famille_id(self):
        """Efface la sous-famille quand la famille est modifiée"""
        if self.is_famille_id:
            # Si la sous-famille actuelle n'appartient pas à la nouvelle famille, l'effacer
            if self.is_sous_famille_id and self.is_sous_famille_id.parent_id != self.is_famille_id:
                self.is_sous_famille_id = False
        else:
            # Si aucune famille n'est sélectionnée, effacer la sous-famille
            self.is_sous_famille_id = False
