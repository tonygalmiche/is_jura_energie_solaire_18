# -*- coding: utf-8 -*-
import os
from odoo import fields, models, api


class IsDocumentationTag(models.Model):
    _name = 'is.documentation.tag'
    _description = "Tag de documentation"
    _order = 'name'

    name = fields.Char(string="Nom", required=True)
    color = fields.Integer(string="Couleur")


class IsDocumentation(models.Model):
    _name = 'is.documentation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Documentation JES"
    _order = 'name'

    name = fields.Char(string="Nom", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    tag_ids = fields.Many2many(
        'is.documentation.tag',
        string="Tags",
        tracking=True
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'is_documentation_attachment_rel',
        'documentation_id',
        'attachment_id',
        string="Pièces jointes"
    )
    attachment_count = fields.Integer(
        string="Nombre de pièces jointes",
        compute='_compute_attachment_count'
    )

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    @api.onchange('attachment_ids')
    def _onchange_attachment_ids(self):
        """Si le nom est vide, utilise le nom de la dernière pièce jointe sans extension."""
        if not self.name and self.attachment_ids:
            # Filtre les enregistrements existants (avec ID réel) et les trie
            existing_attachments = self.attachment_ids.filtered(lambda a: a.id)
            if existing_attachments:
                last_attachment = existing_attachments.sorted('id', reverse=True)[0]
            else:
                # Si tous les attachements sont nouveaux, prend le dernier de la liste
                last_attachment = self.attachment_ids[-1]
            
            filename = last_attachment.name or ''
            name_without_ext = os.path.splitext(filename)[0]
            if name_without_ext:
                self.name = name_without_ext

    def _link_attachments(self):
        """Lie les pièces jointes au modèle pour qu'elles apparaissent dans le chatter."""
        for record in self:
            record.attachment_ids.filtered(lambda a: a.res_model != self._name or a.res_id != record.id).write({
                'res_model': self._name,
                'res_id': record.id
            })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._link_attachments()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'attachment_ids' in vals:
            self._link_attachments()
        return res
