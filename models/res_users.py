# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_signature = fields.Image("Signature", max_width=500, max_height=200)
