# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

ETAT_SELECTION = [
    ('en_attente', 'En attente de validation'),
    ('valide', 'Validé'),
]

JOURS_SEMAINE = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi']


class IsSuiviTempsSemaine(models.Model):
    _name = 'is.suivi.temps.semaine'
    _description = 'Suivi du temps de la semaine'
    _rec_name = 'name'
    _order = 'semaine desc, salarie_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom', compute='_compute_name', store=True)
    salarie_id = fields.Many2one(
        'hr.employee', string='Salarié', required=True, index=True, tracking=True,
        ondelete='cascade',
    )
    semaine = fields.Char(
        string='Semaine', required=True, index=True, tracking=True,
        help='Format AAAA-SXX (ex: 2026-S19)',
    )
    date_debut = fields.Date(string='Date de début', required=True, tracking=True)
    date_fin = fields.Date(string='Date de fin', required=True, tracking=True)
    etat = fields.Selection(
        ETAT_SELECTION, string='État', default='en_attente',
        required=True, index=True, tracking=True,
    )
    ligne_ids = fields.One2many(
        'is.suivi.temps.semaine.ligne', 'semaine_id',
        string='Lignes', copy=False,
    )
    total_temps_travaille = fields.Float(
        string='Total temps travaillé', compute='_compute_totaux', store=True, tracking=True
    )
    total_nuitees = fields.Integer(
        string='Nuitées', compute='_compute_totaux', store=True, tracking=True
    )
    total_paniers = fields.Integer(
        string='Paniers', compute='_compute_totaux', store=True, tracking=True
    )

    _sql_constraints = [
        ('unique_salarie_semaine', 'UNIQUE(salarie_id, semaine)',
         'Une fiche de suivi existe déjà pour ce salarié et cette semaine !'),
    ]

    @api.depends('salarie_id', 'semaine')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.salarie_id:
                parts.append(rec.salarie_id.name)
            if rec.semaine:
                parts.append(rec.semaine)
            rec.name = ' – '.join(parts) if parts else '/'

    @api.depends('ligne_ids.temps_travaille', 'ligne_ids.nuitee', 'ligne_ids.panier')
    def _compute_totaux(self):
        for rec in self:
            rec.total_temps_travaille = sum(rec.ligne_ids.mapped('temps_travaille'))
            rec.total_nuitees = sum(1 for l in rec.ligne_ids if l.nuitee)
            rec.total_paniers = sum(1 for l in rec.ligne_ids if l.panier)

    # ------------------------------------------------------------------
    # Bouton de rafraîchissement manuel
    # ------------------------------------------------------------------
    def action_actualiser(self):
        """Actualise la fiche depuis les saisies du temps (si non validée)."""
        for rec in self:
            if rec.etat == 'valide':
                continue
            rec._actualiser_lignes()

    def action_valider(self):
        """Valide la fiche : elle ne sera plus modifiée par le cron."""
        self.write({'etat': 'valide'})

    def action_remettre_en_attente(self):
        """Remet la fiche en attente de validation."""
        self.write({'etat': 'en_attente'})

    # ------------------------------------------------------------------
    # Méthode principale : créer/actualiser les lignes
    # ------------------------------------------------------------------
    def _actualiser_lignes(self):
        """Recrée les lignes à partir des saisies is.suivi.temps.saisie."""
        self.ensure_one()
        if self.etat == 'valide':
            return

        # Récupérer l'utilisateur lié à l'employé
        employee = self.salarie_id
        user = employee.user_id
        if not user:
            return

        # Supprimer les lignes existantes et recréer
        self.ligne_ids.unlink()

        # Parcourir chaque jour de Lundi à Vendredi
        current_date = self.date_debut
        while current_date <= self.date_fin:
            if current_date.weekday() < 5:  # Lundi=0 … Vendredi=4
                saisie = self.env['is.suivi.temps.saisie'].search([
                    ('utilisateur_id', '=', user.id),
                    ('date', '=', current_date),
                ], limit=1)

                vals = {
                    'semaine_id': self.id,
                    'date': current_date,
                }
                if saisie:
                    vals.update({
                        'heure_arrivee': saisie.heure_debut or 0.0,
                        'temps_pause': saisie.temps_pose or 0.0,
                        'heure_depart': saisie.heure_fin or 0.0,
                        'temps_route': saisie.heure_route or 0.0,
                        'nuitee': saisie.nuitee,
                        'panier': saisie.panier,
                    })
                self.env['is.suivi.temps.semaine.ligne'].create(vals)
            current_date += timedelta(days=1)

    # ------------------------------------------------------------------
    # Tâche cron : crée/actualise les fiches de la semaine précédente
    # ------------------------------------------------------------------
    @api.model
    def cron_creer_fiches_semaine(self):
        """Tâche cron journalière : crée ou actualise les fiches des semaines précédentes."""
        NB_SEMAINES = 3  # Nombre de semaines précédentes à traiter

        today = date.today()
        lundi_semaine_courante = today - timedelta(days=today.weekday())

        for offset in range(1, NB_SEMAINES + 1):
            lundi = lundi_semaine_courante - timedelta(weeks=offset)
            vendredi = lundi + timedelta(days=4)

            annee, num_semaine, _ = lundi.isocalendar()
            semaine_code = f"{annee}-S{num_semaine:02d}"

            employees = self.env['hr.employee'].search([('active', '=', True)])
            for employee in employees:
                fiche = self.search([
                    ('salarie_id', '=', employee.id),
                    ('semaine', '=', semaine_code),
                ], limit=1)

                if fiche and fiche.etat == 'valide':
                    continue

                if not fiche:
                    fiche = self.create({
                        'salarie_id': employee.id,
                        'semaine': semaine_code,
                        'date_debut': lundi,
                        'date_fin': vendredi,
                        'etat': 'en_attente',
                    })
                fiche._actualiser_lignes()

            _logger.info(
                'cron_creer_fiches_semaine : fiches traitées pour la semaine %s (%d employés)',
                semaine_code, len(employees),
            )


class IsSuiviTempsSemaineLigne(models.Model):
    _name = 'is.suivi.temps.semaine.ligne'
    _description = 'Ligne du suivi du temps de la semaine'
    _order = 'date'

    semaine_id = fields.Many2one(
        'is.suivi.temps.semaine', string='Semaine',
        required=True, ondelete='cascade', index=True,
    )
    date = fields.Date(string='Date', required=True)
    jour = fields.Char(string='Jour', compute='_compute_jour', store=True)
    heure_arrivee = fields.Float(string="Heure d'arrivée")
    temps_pause = fields.Float(string='Temps de pause')
    heure_depart = fields.Float(string='Heure de départ')
    temps_route = fields.Float(string='Temps de route')
    temps_travaille = fields.Float(
        string='Temps travaillé', compute='_compute_temps_travaille', store=True,
    )
    nuitee = fields.Boolean(string='Nuitée', default=False)
    panier = fields.Boolean(string='Panier', default=False)

    JOURS_FR = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

    @api.depends('date')
    def _compute_jour(self):
        for rec in self:
            if rec.date:
                rec.jour = self.JOURS_FR[rec.date.weekday()]
            else:
                rec.jour = ''

    @api.depends('heure_arrivee', 'heure_depart', 'temps_pause')
    def _compute_temps_travaille(self):
        for rec in self:
            if rec.heure_arrivee and rec.heure_depart:
                rec.temps_travaille = rec.heure_depart - rec.heure_arrivee - (rec.temps_pause or 0.0)
            else:
                rec.temps_travaille = 0.0

    def action_voir_saisie(self):
        self.ensure_one()
        employee = self.semaine_id.salarie_id
        user = employee.user_id
        saisie = self.env['is.suivi.temps.saisie'].search([
            ('utilisateur_id', '=', user.id),
            ('date', '=', self.date),
        ], limit=1)
        if not saisie:
            return {}
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'is.suivi.temps.saisie',
            'res_id': saisie.id,
            'view_mode': 'form',
            'target': 'current',
        }
