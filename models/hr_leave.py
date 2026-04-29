# -*- coding: utf-8 -*-
import logging
from odoo import models, api
from datetime import timedelta

_logger = logging.getLogger(__name__)


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _create_or_update_saisies_conge(self):
        """Crée ou met à jour les IsSuiviTempsSaisie pour cette demande de congés."""
        SaisieModel = self.env['is.suivi.temps.saisie'].sudo()

        for leave in self:
            if not leave.employee_id or not leave.employee_id.user_id:
                continue
            if not leave.date_from or not leave.date_to:
                continue

            user = leave.employee_id.user_id
            conge_type_id = leave.holiday_status_id.id
            date_from = leave.date_from.date()
            date_to = leave.date_to.date()

            current = date_from
            while current <= date_to:
                # Vérifier si une saisie existe pour cet utilisateur à cette date
                existing = SaisieModel.search([
                    ('utilisateur_id', '=', user.id),
                    ('date', '=', current),
                ], limit=1)

                if existing and existing.conge_id.id != leave.id:
                    _logger.info(
                        'hr_leave: saisie existante non liée à ce congé '
                        'pour %s le %s (saisie id=%d, congé id=%d) — ignoré',
                        user.name, current, existing.id, leave.id,
                    )
                    current += timedelta(days=1)
                    continue

                # Récupérer les horaires depuis le calendrier de l'employé
                horaires = SaisieModel._get_horaires_from_calendar(user.id, current)
                if horaires is None:
                    # Jour non travaillé (week-end, pas d'attendance) → on skip
                    _logger.info('hr_leave: %s est un jour non travaillé → ignoré', current)
                    current += timedelta(days=1)
                    continue
                heure_debut = horaires['heure_debut']
                heure_fin = horaires['heure_fin']
                # Pas de temps de pose pour un jour de congé
                temps_pose = 0.0
                duree_ligne = heure_fin - heure_debut

                ligne_vals = {
                    'sequence': 10,
                    'type_travail': 'absence',
                    'conge_type_id': conge_type_id,
                    'duree': duree_ligne,
                }

                if existing:
                    # Mettre à jour la saisie existante liée à ce congé
                    existing.write({
                        'heure_debut': heure_debut,
                        'heure_fin': heure_fin,
                        'temps_pose': temps_pose,
                    })
                    if existing.ligne_ids:
                        existing.ligne_ids[0].write({
                            'type_travail': 'absence',
                            'conge_type_id': conge_type_id,
                            'duree': duree_ligne,
                        })
                    else:
                        existing.write({'ligne_ids': [(0, 0, ligne_vals)]})
                else:
                    SaisieModel.create({
                        'utilisateur_id': user.id,
                        'date': current,
                        'heure_debut': heure_debut,
                        'heure_fin': heure_fin,
                        'temps_pose': temps_pose,
                        'conge_id': leave.id,
                        'ligne_ids': [(0, 0, ligne_vals)],
                    })

                current += timedelta(days=1)

    def _reset_saisies_conge(self):
        """Supprime les IsSuiviTempsSaisie liées à ce congé (refus ou annulation)."""
        SaisieModel = self.env['is.suivi.temps.saisie'].sudo()
        for leave in self:
            saisies = SaisieModel.search([('conge_id', '=', leave.id)])
            if saisies:
                _logger.info(
                    'hr_leave: suppression de %d saisie(s) liée(s) au congé id=%d (%s) suite à refus/annulation',
                    len(saisies), leave.id, leave.employee_id.name,
                )
                saisies.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        leaves._create_or_update_saisies_conge()
        return leaves

    def write(self, vals):
        res = super().write(vals)
        new_state = vals.get('state')
        _logger.info('hr_leave.write: state=%s, vals keys=%s, ids=%s', new_state, list(vals.keys()), self.ids)
        if new_state in ('refuse', 'cancel'):
            _logger.info('hr_leave.write: état refusé/annulé → appel _reset_saisies_conge pour ids=%s', self.ids)
            self._reset_saisies_conge()
        elif new_state in ('confirm', 'validate1', 'validate'):
            _logger.info('hr_leave.write: état confirmé/approuvé → appel _create_or_update_saisies_conge pour ids=%s', self.ids)
            self._create_or_update_saisies_conge()
        elif any(f in vals for f in ['date_from', 'date_to', 'employee_id', 'holiday_status_id']):
            self._create_or_update_saisies_conge()
        return res
