# -*- coding: utf-8 -*-
from odoo import fields, models
from .is_sav import SAV_STATE_SELECTION


class IsSavSousStatut(models.Model):
    _name = 'is.sav.sous.statut'
    _description = "Sous-statut SAV"
    _order = 'state'

    state = fields.Selection(
        SAV_STATE_SELECTION,
        string="Statut",
        required=True,
    )
    line_ids = fields.One2many('is.sav.sous.statut.line', 'sous_statut_id', string="Sous-statuts")


class IsSavSousStatutLine(models.Model):
    _name = 'is.sav.sous.statut.line'
    _description = "Ligne de sous-statut SAV"
    _order = 'sequence,id'

    sous_statut_id = fields.Many2one(
        'is.sav.sous.statut',
        string="Sous-statut",
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string="Séquence", default=10)
    name = fields.Char(string="Nom du sous-statut", required=True)
    color = fields.Integer(
        string="Couleur",
        default=0,
    )
