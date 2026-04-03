# -*- coding: utf-8 -*-
from odoo import fields, models


class IsCalendrierEquipe(models.Model):
    _name = 'is.calendrier.equipe'
    _description = "Équipe calendrier"
    _order = 'name'

    name        = fields.Char("Nom de l'équipe", required=True)
    employee_ids = fields.Many2many(
        'hr.employee',
        'is_calendrier_equipe_employee_rel',
        'equipe_id',
        'employee_id',
        string="Employés",
    )
