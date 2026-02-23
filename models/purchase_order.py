# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_centrale_id = fields.Many2one("is.centrale", string="Centrale", index=True)


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    is_centrale_id = fields.Many2one("is.centrale", string="Centrale", index=True)
    date_order = fields.Datetime(related="order_id.date_order", string="Date commande", store=True)

    @api.onchange('product_id')
    def _onchange_product_id_set_centrale(self):
        """Propage la centrale de l'entête vers la ligne lors de la création."""
        if self.order_id.is_centrale_id and not self.is_centrale_id:
            self.is_centrale_id = self.order_id.is_centrale_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('is_centrale_id') and vals.get('order_id'):
                order = self.env['purchase.order'].browse(vals['order_id'])
                if order.is_centrale_id:
                    vals['is_centrale_id'] = order.is_centrale_id.id
        return super().create(vals_list)
