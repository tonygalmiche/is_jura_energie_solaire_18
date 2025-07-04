# -*- coding: utf-8 -*-
from odoo import fields, models, api  

class IsSav(models.Model):
    _name='is.sav'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "SAV"
    _order='name'

    name            = fields.Char(string="Nom", size=40, required=True, tracking=True)
    centrale_id     = fields.Many2one('is.centrale', string="Centrale", tracking=True)
    date_demande    = fields.Date(string="Date demande", tracking=True)
    degre_urgence   = fields.Selection(
        [
            ('non_urgent', 'Non Urgent'),
            ('inter', 'Inter'),
            ('urgent', 'Urgent'),
        ],
        string="Degré d'urgence",
        tracking=True,
        default='non_urgent'
    )
    date_resolution = fields.Date(string="Date de résolution", tracking=True)
    intervenant_id  = fields.Many2one('res.partner', string="Intervenant", tracking=True)
    ticket_number   = fields.Char(string="N°Ticket", size=40, tracking=True)
    description     = fields.Text(string="Description", tracking=True)
    info_depannage  = fields.Text(string="Informations Dépannage", tracking=True)
    state = fields.Selection(
        [
            ('pas_commence', 'Pas commencé'),
            ('en_cours', 'En Cours'),
            ('en_etude', 'En Etude'),
            ('planifie', 'Planifié'),
            ('termine', 'Terminé'),
        ],
        string="Statut",
        tracking=True,
        default='pas_commence'
    )


