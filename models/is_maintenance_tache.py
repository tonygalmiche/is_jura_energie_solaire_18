# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IsMaintenanceTypeTache(models.Model):
    _name = 'is.maintenance.type.tache'
    _description = "Type de tâche de maintenance"
    _order = 'sequence, id'

    maintenance_id = fields.Many2one('is.maintenance', string="Maintenance", ondelete='cascade')
    centrale_id = fields.Many2one('is.centrale', string="Centrale", related='maintenance_id.centrale_id', store=True)
    sequence = fields.Integer("Ordre", default=10)
    name = fields.Char("Type de tâche", required=True)
    tache_ids = fields.One2many('is.maintenance.tache', 'type_tache_id', string="Tâches", copy=True)
    
    # Champs pour la configuration des modèles
    is_type_champs_photovoltaique = fields.Boolean("Type Champs photovoltaïque", default=False)
    is_type_coffret_dc = fields.Boolean("Type Coffret DC", default=False)
    is_type_onduleur = fields.Boolean("Type Onduleur", default=False)
    
    # Champs pour le numéro d'ordre et lien onduleur
    numero_ordre = fields.Integer("Numéro d'ordre", default=1)
    onduleur_id = fields.Many2one('is.centrale.onduleur', string="Onduleur")
    tache_count = fields.Integer("Nombre de tâches", compute='_compute_tache_count')

    @api.depends('tache_ids')
    def _compute_tache_count(self):
        for record in self:
            record.tache_count = len(record.tache_ids)

    def action_view_taches(self):
        """Ouvrir la liste des tâches de ce type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tâches - %s' % self.name,
            'res_model': 'is.maintenance.tache',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('is_jura_energie_solaire_18.view_is_maintenance_tache_tree').id, 'list'),
                (self.env.ref('is_jura_energie_solaire_18.view_is_maintenance_tache_form').id, 'form'),
            ],
            'domain': [('type_tache_id', '=', self.id)],
            'context': {'default_type_tache_id': self.id},
        }

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = "%s (copie)" % self.name
        return super(IsMaintenanceTypeTache, self).copy(default)


class IsMaintenanceTache(models.Model):
    _name = 'is.maintenance.tache'
    _description = "Tâche de maintenance"
    _order = 'sequence, id'

    type_tache_id = fields.Many2one('is.maintenance.type.tache', string="Type de tâche", required=True, ondelete='cascade')
    sequence = fields.Integer("Ordre", default=10)
    name = fields.Char("Tâche", required=True)
    etat_actuel = fields.Char("État actuel")
    validation_etat = fields.Selection(
        [
            ('oui', 'Oui'),
            ('non', 'Non'),
        ],
        string="Validation état",
    )
    mesure_correction = fields.Char("Mesure de correction")
    validation_mesure = fields.Selection(
        [
            ('oui', 'Oui'),
            ('non', 'Non'),
        ],
        string="Validation mesure",
    )
    date = fields.Date("Date")
