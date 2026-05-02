# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IsFormeJuridique(models.Model):
    _name = 'is.forme.juridique'
    _description = 'Forme juridique'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)


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
    is_centrale_ids = fields.One2many('is.centrale', 'client_id', string="Centrales")
    is_forme_juridique_id = fields.Many2one('is.forme.juridique', string="Forme juridique")
    is_contacts_html = fields.Html(compute='_compute_contacts_html', store=False, string="Tableau des contacts")

    @api.depends('child_ids.name', 'child_ids.function', 'child_ids.phone', 'child_ids.mobile', 'child_ids.email')
    def _compute_contacts_html(self):
        for partner in self:
            contacts = partner.child_ids
            if contacts:
                def get_tel(child):
                    return child.mobile or child.phone or ''

                columns = [
                    ('name',     'Contact',    lambda c: c.name or ''),
                    ('function', 'Poste',      lambda c: c.function or ''),
                    ('_tel',     'Téléphone',  get_tel),
                    ('email',    'Email',      lambda c: c.email or ''),
                ]
                # Ne garder que les colonnes qui ont au moins une valeur
                visible_cols = [
                    (key, label, getter)
                    for key, label, getter in columns
                    if any(getter(c) for c in contacts)
                ]
                header = ''.join(f'<th style="white-space:nowrap">{label}</th>' for _, label, _ in visible_cols)
                rows = ''.join(
                    '<tr>' + ''.join(f'<td>{getter(child)}</td>' for _, _, getter in visible_cols) + '</tr>'
                    for child in contacts
                )
                partner.is_contacts_html = (
                    '<table class="table table-sm table-bordered" style="width:auto;min-width:400px">'
                    f'<thead><tr>{header}</tr></thead>'
                    f'<tbody>{rows}</tbody>'
                    '</table>'
                )
            else:
                partner.is_contacts_html = False
    is_capital_social = fields.Float(string="Capital social (€)")
    is_lieu_rcs = fields.Char(string="Lieu d'immatriculation RCS")
    is_code_naf = fields.Char(string="Code NAF")

    def action_open_contact(self):
        """Ouvrir la fiche du contact"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
