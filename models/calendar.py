# -*- coding: utf-8 -*-
from odoo import fields, models, api  


class calendar_event(models.Model):
    _inherit = "calendar.event"

    is_sav_id           = fields.Many2one('is.sav', 'SAV', tracking=True)
    is_maintenance_id   = fields.Many2one('is.maintenance', 'Maintenance', tracking=True)
    is_centrale_id      = fields.Many2one('is.centrale', 'Centrale', tracking=True)
    is_centrale_secteur = fields.Selection(related='is_centrale_id.secteur', string='Secteur centrale', store=True)
    is_equipe_id        = fields.Many2one('is.calendrier.equipe', 'Équipe', tracking=True)
    is_client_id        = fields.Many2one('res.partner', string='Client', compute='_compute_is_client_id', store=True)

    @api.depends('is_centrale_id.client_id', 'is_maintenance_id.client_id', 'is_sav_id.client_id')
    def _compute_is_client_id(self):
        for rec in self:
            rec.is_client_id = (
                rec.is_centrale_id.client_id
                or rec.is_maintenance_id.client_id
                or rec.is_sav_id.client_id
                or False
            )
    is_contacts_html    = fields.Html(related='is_centrale_id.is_client_contacts_html', store=False, string='')
    is_adresse          = fields.Char(string='Adresse', compute='_compute_is_adresse', store=False)
    is_maps_url         = fields.Char(string='Maps', compute='_compute_is_maps_url', store=False)

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
