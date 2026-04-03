# -*- coding: utf-8 -*-
from odoo import fields, models, api  


class calendar_event(models.Model):
    _inherit = "calendar.event"

    is_sav_id           = fields.Many2one('is.sav', 'SAV', tracking=True)
    is_maintenance_id   = fields.Many2one('is.maintenance', 'Maintenance', tracking=True)
    is_centrale_id      = fields.Many2one('is.centrale', 'Centrale', tracking=True)
    is_centrale_secteur = fields.Selection(related='is_centrale_id.secteur', string='Secteur centrale', store=True)
    is_equipe_id        = fields.Many2one('is.calendrier.equipe', 'Équipe', tracking=True)
