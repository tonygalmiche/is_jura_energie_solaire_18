# -*- coding: utf-8 -*-
from odoo import fields, models, api  


class calendar_event(models.Model):
    _inherit = "calendar.event"

    is_sav_id         = fields.Many2one('is.sav', 'SAV', tracking=True)
    is_maintenance_id = fields.Many2one('is.maintenance', 'Maintenance', tracking=True)
