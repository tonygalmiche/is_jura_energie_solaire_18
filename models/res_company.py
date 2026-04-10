# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # is_pdf_background_image = fields.Binary(
    #     string="Image de fond PDF",
    #     attachment=True,
    # )

    is_pdf_background = fields.Binary(
        string="PDF de fond (papier-en-tête)",
        attachment=True,
        help="PDF d'une page servant de fond pour les rapports PDF (fusionné en arrière-plan)",
    )

    # is_pdf_bg_header = fields.Binary(
    #     string="Fond PDF - En-tête",
    #     attachment=True,
    #     help="Partie haute du papier-en-tête (52mm), affichée dans le header des rapports PDF",
    # )

    # is_pdf_bg_body = fields.Binary(
    #     string="Fond PDF - Corps",
    #     attachment=True,
    #     help="Partie centrale du papier-en-tête, affichée en fond du corps des rapports PDF",
    # )

    # is_pdf_bg_footer = fields.Binary(
    #     string="Fond PDF - Pied de page",
    #     attachment=True,
    #     help="Partie basse du papier-en-tête (32mm), affichée dans le footer des rapports PDF",
    # )

    is_gestionnaire_administrative_id = fields.Many2one(
        'res.users',
        string="Gestionnaire administrative",
    )

    is_conditions_generales_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='is_company_conditions_generales_rel',
        column1='company_id',
        column2='attachment_id',
        string="Conditions générales",
    )
