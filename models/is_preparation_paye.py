# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta


class IsPreparationPaye(models.Model):
    _name = 'is.preparation.paye'
    _description = 'Préparation Paye'
    _order = 'name desc'
    _rec_name = 'name'

    name = fields.Char(string='Numéro', readonly=True, copy=False, default='Nouveau')
    date_debut = fields.Date(string='Date de début', required=True)
    date_fin = fields.Date(string='Date de fin', required=True)
    employe_ids = fields.One2many('is.preparation.paye.employe', 'preparation_id', string='Employés')
    ligne_ids = fields.One2many('is.preparation.paye.ligne', 'preparation_id', string='Lignes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('is.preparation.paye') or 'Nouveau'
        return super().create(vals_list)

    def _get_heures_prevues_semaine(self, user, semaine):
        """Calcule les heures prévues pour un utilisateur sur une semaine
        à partir du calendrier de travail de l'employé.
        Seuls les jours compris dans la période de la préparation sont comptés.
        """
        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if not employee or not employee.resource_calendar_id:
            return 0.0

        calendar = employee.resource_calendar_id

        # Parser la semaine "YYYY-SXX"
        parts = semaine.split('-S')
        year, week = int(parts[0]), int(parts[1])

        total = 0.0
        for day_num in range(1, 8):  # 1=Lundi … 7=Dimanche
            current_date = date.fromisocalendar(year, week, day_num)

            # Ne compter que les jours dans la période
            if current_date < self.date_debut or current_date > self.date_fin:
                continue

            dayofweek = str(current_date.weekday())
            attendances = calendar.attendance_ids.filtered(
                lambda a, dow=dayofweek, d=current_date:
                    a.dayofweek == dow and
                    a.day_period != 'lunch' and
                    (not a.date_from or a.date_from <= d) and
                    (not a.date_to or a.date_to >= d)
            )
            total += sum(att.hour_to - att.hour_from for att in attendances)

        return total

    def action_voir_toutes_lignes(self):
        """Ouvre toutes les lignes de tous les employés."""
        self.ensure_one()
        return {
            'name': f'Toutes les lignes – {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'is.preparation.paye.ligne',
            'view_mode': 'list',
            'domain': [('preparation_id', '=', self.id)],
            'context': {'default_preparation_id': self.id},
        }

    def action_generer(self):
        """Génère les lignes de préparation paye en analysant les IsSuiviTemps de la période."""
        self.ensure_one()

        # Supprimer les lignes et employés existants
        self.ligne_ids.unlink()
        self.employe_ids.unlink()

        # Rechercher tous les suivis de temps dans la période
        suivis = self.env['is.suivi.temps'].sudo().search([
            ('date', '>=', self.date_debut),
            ('date', '<=', self.date_fin),
        ])

        if not suivis:
            return

        # Utilisateurs distincts
        users = suivis.mapped('utilisateur_id')

        lignes_vals = []
        for user in users:
            user_suivis = suivis.filtered(lambda s: s.utilisateur_id == user)

            # Grouper par semaine ISO
            weeks = {}
            for suivi in user_suivis:
                iso = suivi.date.isocalendar()
                week_key = f"{iso[0]}-S{iso[1]}"
                weeks.setdefault(week_key, self.env['is.suivi.temps'])
                weeks[week_key] |= suivi

            for week_key in sorted(weeks.keys()):
                week_suivis = weeks[week_key]

                # --- Nombre de jours travaillés (dates distinctes hors absence) ---
                dates_travaillees = set()
                for s in week_suivis:
                    if s.type_travail != 'absence':
                        dates_travaillees.add(s.date)
                nb_jour_travaille = len(dates_travaillees)

                # --- Nombre d'heures prévues (calendrier employé) ---
                nb_heure_prevue = self._get_heures_prevues_semaine(user, week_key)

                # --- Nombre d'heures travaillées (hors absences) ---
                nb_heure_travaille = sum(s.duree for s in week_suivis if s.type_travail != 'absence')

                # --- Heures supplémentaires (> 35 h) ---
                heures_sup = max(0.0, nb_heure_travaille - 35.0)

                # --- HS 25 % (de 35 à 43 h) ---
                hs_25 = min(heures_sup, 8.0)

                # --- HS 50 % (> 43 h) ---
                hs_50 = max(0.0, nb_heure_travaille - 43.0)

                # --- Heures dimanche ---
                nb_heure_dimanche = sum(
                    s.duree for s in week_suivis
                    if s.date.weekday() == 6 and s.type_travail != 'absence'
                )

                # --- Congé CP (en jours) ---
                dates_cp = set()
                for s in week_suivis:
                    if s.type_travail == 'absence' and s.absence == 'cp':
                        dates_cp.add(s.date)
                conge_cp = len(dates_cp)

                # --- Congé événement (en jours) ---
                dates_conge_evt = set()
                for s in week_suivis:
                    if s.type_travail == 'absence' and s.absence in ('conge', 'evenement'):
                        dates_conge_evt.add(s.date)
                conge_evenement = len(dates_conge_evt)

                # --- Récupération (en négatif) ---
                recuperation = -sum(
                    s.duree for s in week_suivis
                    if s.type_travail == 'absence' and s.absence == 'recup'
                )

                # --- Heure supplémentaire à payer (heures sup + récup) ---
                heure_sup_a_payer = heures_sup + recuperation

                lignes_vals.append({
                    'preparation_id': self.id,
                    'utilisateur_id': user.id,
                    'semaine': week_key,
                    'nb_jour_travaille': nb_jour_travaille,
                    'nb_heure_prevue': nb_heure_prevue,
                    'nb_heure_travaille': nb_heure_travaille,
                    'heures_supplementaire': heures_sup,
                    'hs_25': hs_25,
                    'hs_50': hs_50,
                    'nb_heure_dimanche': nb_heure_dimanche,
                    'conge_cp': conge_cp,
                    'conge_evenement': conge_evenement,
                    'recuperation': recuperation,
                    'heure_sup_a_payer': heure_sup_a_payer,
                })

        self.env['is.preparation.paye.ligne'].create(lignes_vals)

        # Créer les enregistrements employés (sans doublon)
        employe_vals = []
        for user in users:
            employe_vals.append({
                'preparation_id': self.id,
                'utilisateur_id': user.id,
            })
        if employe_vals:
            self.env['is.preparation.paye.employe'].create(employe_vals)

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for record in self:
            if record.date_debut and record.date_fin:
                if record.date_debut > record.date_fin:
                    raise models.ValidationError(
                        "La date de fin doit être postérieure ou égale à la date de début."
                    )


class IsPreparationPayeLigne(models.Model):
    _name = 'is.preparation.paye.ligne'
    _description = 'Ligne de préparation paye'
    _order = 'utilisateur_id, semaine'

    preparation_id = fields.Many2one(
        'is.preparation.paye', string='Préparation paye',
        required=True, ondelete='cascade', index=True,
    )
    utilisateur_id = fields.Many2one(
        'res.users', string='Employé', required=True, index=True,
    )
    semaine = fields.Char(string='Semaine', required=True)
    nb_jour_travaille = fields.Integer(string='Nb jours travaillés')
    nb_heure_prevue = fields.Float(string="Nb heures prévues", digits=(10, 2))
    nb_heure_travaille = fields.Float(string="Nb heures travaillées", digits=(10, 2))
    heures_supplementaire = fields.Float(string='Heures supplémentaires', digits=(10, 2))
    hs_25 = fields.Float(string='HS 25 % (35‑43H)', digits=(10, 2))
    hs_50 = fields.Float(string='HS 50 % (>43H)', digits=(10, 2))
    nb_heure_dimanche = fields.Float(string='Heures dimanche', digits=(10, 2))
    conge_cp = fields.Float(string='Congé CP (j)', digits=(10, 2))
    conge_evenement = fields.Float(string='Congé événement (j)', digits=(10, 2))
    recuperation = fields.Float(string='Récupération', digits=(10, 2))
    heure_sup_a_payer = fields.Float(string='HS à payer', digits=(10, 2))

    def action_voir_suivi_temps(self):
        """Ouvre les enregistrements IsSuiviTemps de l'employé pour cette semaine."""
        self.ensure_one()

        parts = self.semaine.split('-S')
        year, week = int(parts[0]), int(parts[1])
        start_of_week = date.fromisocalendar(year, week, 1)
        end_of_week = date.fromisocalendar(year, week, 7)

        return {
            'name': f'Suivi temps – {self.utilisateur_id.name} – {self.semaine}',
            'type': 'ir.actions.act_window',
            'res_model': 'is.suivi.temps',
            'view_mode': 'list,form',
            'domain': [
                ('utilisateur_id', '=', self.utilisateur_id.id),
                ('date', '>=', str(start_of_week)),
                ('date', '<=', str(end_of_week)),
            ],
        }


class IsPreparationPayeEmploye(models.Model):
    _name = 'is.preparation.paye.employe'
    _description = 'Employé de préparation paye'
    _order = 'utilisateur_id'

    preparation_id = fields.Many2one(
        'is.preparation.paye', string='Préparation paye',
        required=True, ondelete='cascade', index=True,
    )
    utilisateur_id = fields.Many2one(
        'res.users', string='Employé', required=True, index=True,
    )

    def action_voir_lignes_employe(self):
        """Ouvre les lignes de préparation paye pour cet employé."""
        self.ensure_one()
        return {
            'name': f'Semaines – {self.utilisateur_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'is.preparation.paye.ligne',
            'view_mode': 'list',
            'domain': [
                ('preparation_id', '=', self.preparation_id.id),
                ('utilisateur_id', '=', self.utilisateur_id.id),
            ],
        }
