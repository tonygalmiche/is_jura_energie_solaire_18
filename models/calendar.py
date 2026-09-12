# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools import html_escape


class calendar_event(models.Model):
    _inherit = "calendar.event"

    is_sav_id           = fields.Many2one('is.sav', 'SAV', tracking=True)
    is_maintenance_id   = fields.Many2one('is.maintenance', 'Maintenance', tracking=True)
    is_centrale_id      = fields.Many2one('is.centrale', 'Centrale', tracking=True)
    is_centrale_secteur = fields.Selection(related='is_centrale_id.secteur', string='Secteur centrale', store=True)
    is_equipe_id        = fields.Many2one('is.calendrier.equipe', 'Équipe', tracking=True)
    is_client_id        = fields.Many2one('res.partner', string='Client', compute='_compute_is_client_id', store=True)
    is_contacts_html    = fields.Html(related='is_centrale_id.is_client_contacts_html', store=False, string='')
    is_all_attendee_partner_ids = fields.Many2many(
        'res.partner',
        relation='calendar_event_is_all_attendee_partner_rel',
        string='Organisateur + Participants',
        compute='_compute_is_all_attendee_partner_ids',
        store=True,
    )
    is_participants_html = fields.Html(string='Participants', compute='_compute_is_participants_html', store=False, sanitize=False)
    is_adresse          = fields.Char(string='Adresse', compute='_compute_is_adresse', store=False)
    is_maps_url         = fields.Char(string='Maps', compute='_compute_is_maps_url', store=False)

    @api.depends('is_centrale_id.client_id', 'is_maintenance_id.client_id', 'is_sav_id.client_id')
    def _compute_is_client_id(self):
        for rec in self:
            rec.is_client_id = (
                rec.is_centrale_id.client_id
                or rec.is_maintenance_id.client_id
                or rec.is_sav_id.client_id
                or False
            )

    @api.depends('partner_ids', 'user_id.partner_id')
    def _compute_is_all_attendee_partner_ids(self):
        for rec in self:
            rec.is_all_attendee_partner_ids = rec.partner_ids | rec.user_id.partner_id

    @api.depends('is_all_attendee_partner_ids.name', 'user_id.partner_id')
    def _compute_is_participants_html(self):
        for rec in self:
            organizer_partner = rec.user_id.partner_id
            parts = []
            for partner in rec.is_all_attendee_partner_ids:
                name = html_escape(partner.name or '')
                if partner == organizer_partner:
                    parts.append('<b>%s</b>' % name)
                else:
                    parts.append(name)
            if parts:
                rec.is_participants_html = (
                    '<i class="fa fa-address-book me-1" title="Participants"></i>' + ', '.join(parts)
                )
            else:
                rec.is_participants_html = False

    @api.depends('is_centrale_id.adresse', 'is_maintenance_id.centrale_id.adresse', 'is_sav_id.adresse')
    def _compute_is_adresse(self):
        for rec in self:
            rec.is_adresse = (
                rec.is_centrale_id.adresse
                or rec.is_maintenance_id.centrale_id.adresse
                or rec.is_sav_id.adresse
                or False
            )

    @api.depends('is_centrale_id.localisation_google_maps_url', 'is_maintenance_id.centrale_id.localisation_google_maps_url', 'is_sav_id.centrale_id.localisation_google_maps_url')
    def _compute_is_maps_url(self):
        for rec in self:
            rec.is_maps_url = (
                rec.is_centrale_id.localisation_google_maps_url
                or rec.is_maintenance_id.centrale_id.localisation_google_maps_url
                or rec.is_sav_id.centrale_id.localisation_google_maps_url
                or False
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            lead = rec.opportunity_id
            if lead and not lead.is_date_premiere_reunion and rec.start:
                start_date = rec.start.date()
                delta = (start_date - lead.create_date.date()).days
                lead.write({
                    'is_date_premiere_reunion': start_date,
                    'is_delai_prise_en_compte': delta,
                })
        return records
