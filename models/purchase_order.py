# -*- coding: utf-8 -*-
import base64
import io

from PyPDF2 import PdfReader, PdfWriter

from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_centrale_id = fields.Many2one("is.centrale", string="Centrale", index=True)
    is_objet = fields.Char(string="Objet de la commande")

    def action_print_pdf_with_background(self):
        """Génère le PDF du bon de commande avec le papier-en-tête en fond."""
        self.ensure_one()
        bg_pdf_data = self.company_id.is_pdf_background
        if not bg_pdf_data:
            raise UserError("Veuillez d'abord configurer le PDF de fond dans la fiche société (onglet JES).")

        # 1. Générer le PDF Odoo standard
        report = self.env.ref('purchase.action_report_purchase_order')
        pdf_content, _content_type = report._render_qweb_pdf(report.id, [self.id])

        # 2. Lire le PDF de fond (une page)
        bg_reader = PdfReader(io.BytesIO(base64.b64decode(bg_pdf_data)))
        bg_page = bg_reader.pages[0]

        # 3. Fusionner : fond en arrière-plan de chaque page
        content_reader = PdfReader(io.BytesIO(pdf_content))
        writer = PdfWriter()
        for page in content_reader.pages:
            from copy import copy
            bg_copy = copy(bg_page)
            bg_copy.merge_page(page)
            writer.add_page(bg_copy)

        # 4. Écrire le PDF final
        output = io.BytesIO()
        writer.write(output)
        merged_pdf = output.getvalue()

        # 5. Créer une pièce jointe et retourner l'action de téléchargement
        filename = "Bon de commande - %s.pdf" % self.name
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(merged_pdf),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }


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
