# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, time
import pytz


class IsSuiviTemps(models.Model):
    _name = 'is.suivi.temps'
    _description = 'Suivi du temps'
    _rec_name = "name"
    _order = 'date_debut desc'

    name = fields.Char(string='Nom', compute='_compute_name', store=True)
    utilisateur_id = fields.Many2one('res.users', string='Utilisateur', required=True, default=lambda self: self.env.user, index=True)
    date = fields.Date(string='Date', store=True, required=True, default=fields.Date.context_today)
    heure_debut = fields.Float(string='Heure début', store=True, required=True)
    heure_fin = fields.Float(string='Heure fin', store=True, required=True)
    date_debut = fields.Datetime(string='Heure de début', compute='_compute_datetimes', store=True, readonly=False)
    date_fin = fields.Datetime(string='Heure de fin', compute='_compute_datetimes', store=True, readonly=False)
    type_travail = fields.Selection([
            ('chantier', 'Chantier'), ('bureau', 'Bureau'), ('atelier', 'Atelier'), ('sav', 'SAV'), ('absence', 'Absence')
        ], string='Type de travail', default='bureau', required=True, index=True)
    centrale_id = fields.Many2one('is.centrale', string='Centrale', index=True)
    absence = fields.Selection([('recup', 'Récup'), ('cp', 'CP'), ('sans_solde', 'Sans solde'), ('conge', 'Congé'), ('evenement', 'Evenement'), ('repos', 'Repos')], string='Absence', index=True)
    heure_route = fields.Float(string='Heure de route', help='Temps de route en heures et minutes')
    duree = fields.Float(string='Durée', compute='_compute_duree', store=True, help='Durée en heures')
    duree_hors_deplacement = fields.Float(string='Durée hors déplacement', compute='_compute_duree_hors_deplacement', store=True, help='Durée en heures sans le temps de route')
    commentaire = fields.Text(string='Commentaire')
    panier = fields.Boolean(string='Panier', default=False)
    nuitee = fields.Boolean(string='Nuitée', default=False)

    @api.model
    def default_get(self, fields_list):
        res = super(IsSuiviTemps, self).default_get(fields_list)
        print("=== DEFAULT_GET ===")
        print(f"fields_list: {fields_list}")
        print(f"res initial: {res}")
        
        # Si date_debut et date_fin sont présents (création depuis calendrier)
        # extraire la date et les heures
        if 'date_debut' in res and 'date_fin' in res:
            dt_debut = fields.Datetime.to_datetime(res['date_debut'])
            dt_fin = fields.Datetime.to_datetime(res['date_fin'])
            # Convertir de UTC vers heure locale
            tz = pytz.timezone(self.env.user.tz or 'Europe/Paris')
            dt_debut_utc = pytz.UTC.localize(dt_debut)
            dt_fin_utc = pytz.UTC.localize(dt_fin)
            dt_debut_local = dt_debut_utc.astimezone(tz)
            dt_fin_local = dt_fin_utc.astimezone(tz)
            # Mettre à jour avec les bonnes valeurs
            res['date'] = dt_debut_local.date()
            res['heure_debut'] = dt_debut_local.hour + dt_debut_local.minute / 60.0
            res['heure_fin'] = dt_fin_local.hour + dt_fin_local.minute / 60.0
        else:
            # Création manuelle - valeurs par défaut 8h-17h
            if 'heure_debut' in fields_list and 'heure_debut' not in res:
                res['heure_debut'] = 8.0
            if 'heure_fin' in fields_list and 'heure_fin' not in res:
                res['heure_fin'] = 17.0
        
        print(f"res final: {res}")
        return res

    @api.depends('date', 'heure_debut', 'heure_fin')
    def _compute_datetimes(self):
        for record in self:
            # Ne calculer que si les valeurs sont définies et cohérentes
            if record.date and record.heure_debut is not False and record.heure_fin is not False:
                hours = int(record.heure_debut)
                minutes = int((record.heure_debut - hours) * 60)
                # Créer datetime en heure locale
                tz = pytz.timezone(record.env.user.tz or 'Europe/Paris')
                local_dt = tz.localize(datetime.combine(record.date, time(hours, minutes)))
                # Convertir en UTC pour le stockage
                record.date_debut = local_dt.astimezone(pytz.UTC).replace(tzinfo=None)
                
                hours = int(record.heure_fin)
                minutes = int((record.heure_fin - hours) * 60)
                # Créer datetime en heure locale
                local_dt = tz.localize(datetime.combine(record.date, time(hours, minutes)))
                # Convertir en UTC pour le stockage
                record.date_fin = local_dt.astimezone(pytz.UTC).replace(tzinfo=None)

    @api.onchange('date_debut')
    def _onchange_date_debut(self):
        print(f"=== ONCHANGE date_debut: {self.date_debut} ===")
        if self.date_debut:
            # Convertir de UTC vers heure locale
            tz = pytz.timezone(self.env.user.tz or 'Europe/Paris')
            dt_utc = pytz.UTC.localize(self.date_debut)
            dt_local = dt_utc.astimezone(tz)
            self.date = dt_local.date()
            self.heure_debut = dt_local.hour + dt_local.minute / 60.0
            print(f"  -> date: {self.date}, heure_debut: {self.heure_debut}")

    @api.onchange('date_fin')
    def _onchange_date_fin(self):
        print(f"=== ONCHANGE date_fin: {self.date_fin} ===")
        if self.date_fin:
            # Convertir de UTC vers heure locale
            tz = pytz.timezone(self.env.user.tz or 'Europe/Paris')
            dt_utc = pytz.UTC.localize(self.date_fin)
            dt_local = dt_utc.astimezone(tz)
            if not self.date:
                self.date = dt_local.date()
            self.heure_fin = dt_local.hour + dt_local.minute / 60.0
            print(f"  -> date: {self.date}, heure_fin: {self.heure_fin}")

    @api.model_create_multi
    def create(self, vals_list):
        print("=== CREATE ===")
        for vals in vals_list:
            print(f"vals initial: {vals}")
            # Si date_debut et date_fin sont fournis (création depuis calendrier), calculer date et heures
            if 'date_debut' in vals and 'date_fin' in vals:
                dt_debut = fields.Datetime.to_datetime(vals['date_debut'])
                dt_fin = fields.Datetime.to_datetime(vals['date_fin'])
                print(f"dt_debut (from vals): {dt_debut}")
                print(f"dt_fin (from vals): {dt_fin}")
                # Convertir de UTC vers heure locale
                tz = pytz.timezone(self.env.user.tz or 'Europe/Paris')
                dt_debut_utc = pytz.UTC.localize(dt_debut)
                dt_fin_utc = pytz.UTC.localize(dt_fin)
                dt_debut_local = dt_debut_utc.astimezone(tz)
                dt_fin_local = dt_fin_utc.astimezone(tz)
                print(f"dt_debut_local: {dt_debut_local}")
                print(f"dt_fin_local: {dt_fin_local}")
                vals['date'] = dt_debut_local.date()
                vals['heure_debut'] = dt_debut_local.hour + dt_debut_local.minute / 60.0
                vals['heure_fin'] = dt_fin_local.hour + dt_fin_local.minute / 60.0
                print(f"vals final: {vals}")
        return super(IsSuiviTemps, self).create(vals_list)

    def write(self, vals):
        # Si date_debut ou date_fin sont modifiés directement (calendrier), mettre à jour les autres champs
        if 'date_debut' in vals and vals.get('date_debut'):
            dt_utc = fields.Datetime.to_datetime(vals['date_debut'])
            # Convertir de UTC vers heure locale
            tz = pytz.timezone(self.env.user.tz or 'Europe/Paris')
            dt_utc = pytz.UTC.localize(dt_utc)
            dt_local = dt_utc.astimezone(tz)
            vals['date'] = dt_local.date()
            vals['heure_debut'] = dt_local.hour + dt_local.minute / 60.0
        if 'date_fin' in vals and vals.get('date_fin'):
            dt_utc = fields.Datetime.to_datetime(vals['date_fin'])
            # Convertir de UTC vers heure locale
            tz = pytz.timezone(self.env.user.tz or 'Europe/Paris')
            dt_utc = pytz.UTC.localize(dt_utc)
            dt_local = dt_utc.astimezone(tz)
            if 'date' not in vals:
                vals['date'] = dt_local.date()
            vals['heure_fin'] = dt_local.hour + dt_local.minute / 60.0
        return super(IsSuiviTemps, self).write(vals)

    @api.depends('utilisateur_id', 'type_travail', 'centrale_id', 'absence')
    def _compute_name(self):
        for record in self:
            lines = []
            if record.utilisateur_id:
                lines.append(record.utilisateur_id.name)
            if record.type_travail:
                type_label = dict(record._fields['type_travail'].selection).get(record.type_travail)
                lines.append(type_label)
            if record.type_travail == 'chantier' and record.centrale_id:
                lines.append(record.centrale_id.name)
            if record.type_travail == 'absence' and record.absence:
                absence_label = dict(record._fields['absence'].selection).get(record.absence)
                lines.append(absence_label)
            record.name = ' | '.join(lines) if lines else f'Suivi {record.id}'

    @api.depends('date_debut', 'date_fin')
    def _compute_duree(self):
        for record in self:
            if record.date_debut and record.date_fin:
                delta = record.date_fin - record.date_debut
                record.duree = delta.total_seconds() / 3600.0
            else:
                record.duree = 0.0

    @api.depends('duree', 'heure_route')
    def _compute_duree_hors_deplacement(self):
        for record in self:
            record.duree_hors_deplacement = record.duree - (record.heure_route or 0.0)

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for record in self:
            # Ne vérifier que si les deux champs sont remplis
            if record.date_debut and record.date_fin:
                if record.date_debut >= record.date_fin:
                    raise models.ValidationError("L'heure de fin doit être postérieure à l'heure de début.")
                # Vérifier que les dates sont sur la même journée
                if record.date_debut.date() != record.date_fin.date():
                    raise models.ValidationError("La date de début et la date de fin doivent être sur la même journée.")

    @api.constrains('duree_hors_deplacement')
    def _check_duree_hors_deplacement(self):
        for record in self:
            if record.duree_hors_deplacement and record.duree_hors_deplacement > 10.0:
                raise models.ValidationError("La durée hors déplacement ne peut pas être supérieure à 10 heures.")
