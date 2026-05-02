# -*- coding: utf-8 -*-
import logging
import pytz
from odoo import models, api
from datetime import timedelta

_logger = logging.getLogger(__name__)


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    def _sync_saisies_jours_feries(self):
        """Crée ou met à jour les saisies de temps pour chaque employé concerné par ce jour férié."""
        SaisieModel = self.env['is.suivi.temps.saisie'].sudo()

        # Rechercher le type de congé "Jours fériés"
        conge_type = self.env['hr.leave.type'].sudo().search(
            [('name', 'ilike', 'férié')], limit=1
        )
        conge_type_id = conge_type.id if conge_type else False

        for jf in self:
            # On ne traite que les jours fériés globaux (sans ressource spécifique)
            if jf.resource_id:
                continue
            if not jf.date_from or not jf.date_to:
                continue

            # Convertir les datetimes UTC en heure locale de la société
            tz_name = jf.calendar_id.tz or jf.company_id.resource_calendar_id.tz or 'Europe/Paris'
            tz = pytz.timezone(tz_name)
            date_from = pytz.utc.localize(jf.date_from).astimezone(tz).date()
            date_to = pytz.utc.localize(jf.date_to).astimezone(tz).date()

            # Supprimer les anciennes saisies liées à ce jour férié
            old_saisies = SaisieModel.search([('jour_ferie_id', '=', jf.id)])
            if old_saisies:
                _logger.info(
                    'resource_calendar_leaves: suppression de %d saisie(s) existante(s) pour le jour férié id=%d',
                    len(old_saisies), jf.id,
                )
                old_saisies.unlink()

            # Récupérer tous les employés actifs avec un utilisateur
            employees = self.env['hr.employee'].sudo().search([
                ('user_id', '!=', False),
                ('active', '=', True),
            ])

            for employee in employees:
                user = employee.user_id
                current = date_from

                while current <= date_to:
                    # Vérifier si une saisie existe déjà pour cet utilisateur à cette date
                    existing = SaisieModel.search([
                        ('utilisateur_id', '=', user.id),
                        ('date', '=', current),
                    ], limit=1)

                    if existing and not existing.jour_ferie_id:
                        # Saisie existante non liée à un jour férié → on ne l'écrase pas
                        _logger.info(
                            'resource_calendar_leaves: saisie existante non liée à un jour férié '
                            'pour %s le %s (saisie id=%d) — ignorée',
                            user.name, current, existing.id,
                        )
                        current += timedelta(days=1)
                        continue

                    # Récupérer les horaires depuis le calendrier de l'employé
                    horaires = SaisieModel._get_horaires_from_calendar(user.id, current)
                    if horaires is None:
                        # Jour non travaillé (week-end) → on skip
                        _logger.info(
                            'resource_calendar_leaves: %s est un jour non travaillé pour %s → ignoré',
                            current, user.name,
                        )
                        current += timedelta(days=1)
                        continue

                    heure_debut = horaires['heure_debut']
                    heure_fin = horaires['heure_fin']
                    temps_pose = horaires.get('temps_pose', 0.0)
                    duree_ligne = heure_fin - heure_debut - temps_pose

                    ligne_vals = {
                        'sequence': 10,
                        'type_travail': 'absence',
                        'conge_type_id': conge_type_id,
                        'duree': duree_ligne,
                    }

                    SaisieModel.create({
                        'utilisateur_id': user.id,
                        'date': current,
                        'heure_debut': heure_debut,
                        'heure_fin': heure_fin,
                        'temps_pose': temps_pose,
                        'jour_ferie_id': jf.id,
                        'ligne_ids': [(0, 0, ligne_vals)],
                    })
                    _logger.info(
                        'resource_calendar_leaves: saisie créée pour %s le %s (jour férié: %s)',
                        user.name, current, jf.name,
                    )

                    current += timedelta(days=1)

    def _reset_saisies_jours_feries(self):
        """Supprime les saisies liées à ces jours fériés."""
        SaisieModel = self.env['is.suivi.temps.saisie'].sudo()
        for jf in self:
            saisies = SaisieModel.search([('jour_ferie_id', '=', jf.id)])
            if saisies:
                _logger.info(
                    'resource_calendar_leaves: suppression de %d saisie(s) pour le jour férié id=%d (%s)',
                    len(saisies), jf.id, jf.name,
                )
                saisies.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_saisies_jours_feries()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ['date_from', 'date_to', 'resource_id', 'name']):
            self._sync_saisies_jours_feries()
        return res

    def unlink(self):
        self._reset_saisies_jours_feries()
        return super().unlink()
