# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, time
import pytz


# Listes de sélection communes
TYPE_TRAVAIL_SELECTION = [
    ('chantier', 'Chantier'),
    ('bureau', 'Bureau'),
    ('atelier', 'Atelier'),
    ('sav', 'SAV'),
    ('absence', 'Absence')
]


class IsSuiviTemps(models.Model):
    _name = 'is.suivi.temps'
    _description = 'Suivi du temps'
    _rec_name = "name"
    _order = 'date_debut desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom', compute='_compute_name', store=True)
    utilisateur_id = fields.Many2one('res.users', string='Utilisateur', required=True, default=lambda self: self.env.user, index=True, tracking=True)
    date = fields.Date(string='Date', store=True, required=True, default=fields.Date.context_today, tracking=True)
    heure_debut = fields.Float(string='Heure début', store=True, required=True, tracking=True)
    heure_fin = fields.Float(string='Heure fin', store=True, required=True, tracking=True)
    date_debut = fields.Datetime(string='Heure de début', compute='_compute_datetimes', store=True, readonly=False, tracking=True)
    date_fin = fields.Datetime(string='Heure de fin', compute='_compute_datetimes', store=True, readonly=False, tracking=True)
    type_travail = fields.Selection(TYPE_TRAVAIL_SELECTION, string='Type de travail', default='bureau', required=True, index=True, tracking=True)
    centrale_id = fields.Many2one('is.centrale', string='Centrale', index=True, tracking=True)
    absence = fields.Selection([('recup', 'Récup'), ('cp', 'CP'), ('sans_solde', 'Sans solde'), ('conge', 'Congé'), ('evenement', 'Evenement'), ('repos', 'Repos')], string='Absence', index=True, tracking=True)
    heure_route = fields.Float(string='Heure de route', help='Temps de route en heures et minutes', tracking=True)
    duree = fields.Float(string='Durée', compute='_compute_duree', store=True, help='Durée en heures')
    duree_hors_deplacement = fields.Float(string='Durée hors déplacement', compute='_compute_duree_hors_deplacement', store=True, help='Durée en heures sans le temps de route')
    commentaire = fields.Text(string='Commentaire', tracking=True)
    panier = fields.Boolean(string='Panier', default=False, tracking=True)
    nuitee = fields.Boolean(string='Nuitée', default=False, tracking=True)

    def _get_tz(self):
        """Retourne le timezone de l'utilisateur"""
        return pytz.timezone(self.env.user.tz or 'Europe/Paris')
    
    def _utc_to_local(self, dt_utc):
        """Convertit un datetime UTC (naive) vers le timezone local"""
        if not dt_utc:
            return None
        dt_utc = pytz.UTC.localize(dt_utc) if not dt_utc.tzinfo else dt_utc
        return dt_utc.astimezone(self._get_tz())
    
    def _local_to_utc(self, dt_local):
        """Convertit un datetime local (naive) vers UTC (naive)"""
        if not dt_local:
            return None
        dt_local = self._get_tz().localize(dt_local) if not dt_local.tzinfo else dt_local
        return dt_local.astimezone(pytz.UTC).replace(tzinfo=None)
    
    def _float_to_time(self, float_hour):
        """Convertit une heure en float (8.5) vers un objet time"""
        # Gérer les cas où l'heure dépasse 24h (normaliser à 0-23)
        float_hour = float_hour % 24
        hours = int(float_hour)
        minutes = int((float_hour - hours) * 60)
        return time(hours, minutes)
    
    def _datetime_to_float_hour(self, dt):
        """Extrait l'heure en float d'un datetime"""
        return dt.hour + dt.minute / 60.0

    @api.model
    def default_get(self, fields_list):
        res = super(IsSuiviTemps, self).default_get(fields_list)
        
        # Si date_debut et date_fin sont présents (création depuis calendrier)
        if 'date_debut' in res and 'date_fin' in res:
            dt_debut_local = self._utc_to_local(fields.Datetime.to_datetime(res['date_debut']))
            dt_fin_local = self._utc_to_local(fields.Datetime.to_datetime(res['date_fin']))
            res['date'] = dt_debut_local.date()
            res['heure_debut'] = self._datetime_to_float_hour(dt_debut_local)
            res['heure_fin'] = self._datetime_to_float_hour(dt_fin_local)
        else:
            # Création manuelle - valeurs par défaut 8h-17h
            if 'heure_debut' in fields_list and 'heure_debut' not in res:
                res['heure_debut'] = 8.0
            if 'heure_fin' in fields_list and 'heure_fin' not in res:
                res['heure_fin'] = 17.0
        
        return res

    @api.depends('date', 'heure_debut', 'heure_fin')
    def _compute_datetimes(self):
        for record in self:
            if record.date and record.heure_debut is not False and record.heure_fin is not False:
                # Convertir date + heure_debut -> date_debut (UTC)
                dt_local = datetime.combine(record.date, record._float_to_time(record.heure_debut))
                record.date_debut = record._local_to_utc(dt_local)
                
                # Convertir date + heure_fin -> date_fin (UTC)
                dt_local = datetime.combine(record.date, record._float_to_time(record.heure_fin))
                record.date_fin = record._local_to_utc(dt_local)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Si date_debut et date_fin sont fournis (création depuis calendrier)
            if 'date_debut' in vals and 'date_fin' in vals:
                dt_debut_local = self._utc_to_local(fields.Datetime.to_datetime(vals['date_debut']))
                dt_fin_local = self._utc_to_local(fields.Datetime.to_datetime(vals['date_fin']))
                vals['date'] = dt_debut_local.date()
                vals['heure_debut'] = self._datetime_to_float_hour(dt_debut_local)
                vals['heure_fin'] = self._datetime_to_float_hour(dt_fin_local)
        return super(IsSuiviTemps, self).create(vals_list)

    def write(self, vals):
        # Si date_debut ou date_fin modifiés (drag & drop calendrier)
        if 'date_debut' in vals and vals.get('date_debut'):
            dt_local = self._utc_to_local(fields.Datetime.to_datetime(vals['date_debut']))
            vals['date'] = dt_local.date()
            vals['heure_debut'] = self._datetime_to_float_hour(dt_local)
        if 'date_fin' in vals and vals.get('date_fin'):
            dt_local = self._utc_to_local(fields.Datetime.to_datetime(vals['date_fin']))
            if 'date' not in vals:
                vals['date'] = dt_local.date()
            vals['heure_fin'] = self._datetime_to_float_hour(dt_local)
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


class IsSuiviTempsSaisie(models.Model):
    _name = 'is.suivi.temps.saisie'
    _description = 'Saisie simplifiée du temps'
    _rec_name = "utilisateur_id"
    _order = 'date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    utilisateur_id = fields.Many2one('res.users', string='Utilisateur', required=True, default=lambda self: self.env.user, index=True, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, index=True, tracking=True)
    heure_debut = fields.Float(string='Heure de début', help='Heure de début de journée', tracking=True)
    heure_fin = fields.Float(string='Heure de fin', help='Heure de fin de journée', tracking=True)
    heure_route = fields.Float(string='Heure de route', help='Temps de route en heures', tracking=True)
    temps_pose = fields.Float(string='Temps de pose', help='Temps de pause en heures', tracking=True)
    temps_travail = fields.Float(string='Temps de travail', compute='_compute_temps', store=True, help='Temps de travail effectif')
    temps_presence = fields.Float(string='Temps de présence', compute='_compute_temps', store=True, help='Temps de présence total')
    nuitee = fields.Boolean(string='Nuitée', default=False, tracking=True)
    panier = fields.Boolean(string='Panier', default=False, tracking=True)
    commentaire = fields.Text(string='Commentaire', tracking=True)
    ligne_ids = fields.One2many('is.suivi.temps.saisie.ligne', 'saisie_id', string='Lignes de saisie', copy=True)
    has_sav = fields.Boolean(string='Contient du SAV', compute='_compute_has_sav', store=False)

    def _get_horaires_from_calendar(self, user_id, date):
        """
        Récupère les horaires de travail à partir du calendrier de l'employé
        Retourne un dict avec heure_debut, heure_fin, temps_pose
        """
        result = {'heure_debut': 8.0, 'heure_fin': 17.0, 'temps_pose': 0.0}
        
        # Chercher l'employé lié à cet utilisateur
        employee = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
        
        if not employee or not employee.resource_calendar_id:
            return result
        
        calendar = employee.resource_calendar_id
        
        # Récupérer le jour de la semaine (0=Lundi, 6=Dimanche)
        dayofweek = str(date.weekday())
        
        # Récupérer les horaires de travail pour ce jour (hors lunch)
        attendances = calendar.attendance_ids.filtered(
            lambda a: a.dayofweek == dayofweek and 
                     a.day_period != 'lunch' and
                     (not a.date_from or a.date_from <= date) and
                     (not a.date_to or a.date_to >= date)
        ).sorted('hour_from')
        
        if attendances:
            # Première plage horaire = heure de début
            # Dernière plage horaire = heure de fin
            result['heure_debut'] = attendances[0].hour_from
            result['heure_fin'] = attendances[-1].hour_to
            
            # Calculer le temps de pause (somme des périodes 'lunch')
            lunch_attendances = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == dayofweek and 
                         a.day_period == 'lunch' and
                         (not a.date_from or a.date_from <= date) and
                         (not a.date_to or a.date_to >= date)
            )
            if lunch_attendances:
                result['temps_pose'] = sum((att.hour_to - att.hour_from) for att in lunch_attendances)
        
        return result

    def _get_default_lignes(self, user_id, date):
        """
        Récupère les lignes du jour précédent pour les mettre par défaut avec durée à 0
        Retourne [] si la date est un lundi (weekday() == 0)
        """
        from datetime import timedelta
        
        # Si c'est un lundi, ne rien retourner
        if date.weekday() == 0:
            return []
        
        # Chercher la saisie du jour précédent pour le même utilisateur
        date_precedente = date - timedelta(days=1)
        saisie_precedente = self.env['is.suivi.temps.saisie'].search([
            ('utilisateur_id', '=', user_id),
            ('date', '=', date_precedente)
        ], limit=1)
        
        if not saisie_precedente or not saisie_precedente.ligne_ids:
            return []
        
        # Créer les lignes avec durée à 0
        lignes = []
        for ligne in saisie_precedente.ligne_ids.sorted('sequence'):
            lignes.append((0, 0, {
                'sequence': ligne.sequence,
                'type_travail': ligne.type_travail,
                'centrale_id': ligne.centrale_id.id if ligne.centrale_id else False,
                'absence': ligne.absence,
                'duree': 0.0,
            }))
        
        return lignes

    @api.model
    def default_get(self, fields_list):
        """Surcharge pour définir les valeurs par défaut à partir des horaires de travail de l'employé"""
        res = super(IsSuiviTempsSaisie, self).default_get(fields_list)
        
        # Récupérer l'utilisateur (soit depuis res, soit l'utilisateur courant)
        user_id = res.get('utilisateur_id') or self.env.user.id
        date = res.get('date') or fields.Date.context_today(self)
        
        # Récupérer les horaires depuis le calendrier
        horaires = self._get_horaires_from_calendar(user_id, date)
        
        # Définir les valeurs par défaut
        if 'heure_debut' in fields_list:
            res['heure_debut'] = horaires['heure_debut']
        if 'heure_fin' in fields_list:
            res['heure_fin'] = horaires['heure_fin']
        if 'temps_pose' in fields_list:
            res['temps_pose'] = horaires['temps_pose']
        
        # Pré-remplir les lignes à partir du jour précédent (sauf si lundi)
        if 'ligne_ids' in fields_list:
            res['ligne_ids'] = self._get_default_lignes(user_id, date)
        
        return res

    @api.onchange('date', 'utilisateur_id')
    def _onchange_date_utilisateur(self):
        """Met à jour les horaires quand la date ou l'utilisateur change"""
        if self.date and self.utilisateur_id:
            # Récupérer les horaires depuis le calendrier
            horaires = self._get_horaires_from_calendar(self.utilisateur_id.id, self.date)
            
            # Mettre à jour les champs
            self.heure_debut = horaires['heure_debut']
            self.heure_fin = horaires['heure_fin']
            self.temps_pose = horaires['temps_pose']
            
            # Recharger les lignes à partir du jour précédent (sauf si lundi)
            # On recharge toujours si le formulaire est nouveau (pas d'id)
            if not self.id:
                lignes_default = self._get_default_lignes(self.utilisateur_id.id, self.date)
                # Supprimer toutes les lignes existantes et ajouter les nouvelles
                self.ligne_ids = [(5, 0, 0)]
                if lignes_default:
                    self.ligne_ids = lignes_default

    @api.depends('ligne_ids.type_travail')
    def _compute_has_sav(self):
        for record in self:
            record.has_sav = any(ligne.type_travail == 'sav' for ligne in record.ligne_ids)

    @api.depends('heure_debut', 'heure_fin', 'temps_pose', 'heure_route')
    def _compute_temps(self):
        for record in self:
            if record.heure_debut and record.heure_fin:
                # Temps de présence = heure fin - heure début
                record.temps_presence = record.heure_fin - record.heure_debut
                # Temps de travail = temps présence - temps pose
                record.temps_travail = record.temps_presence - (record.temps_pose or 0.0)
            else:
                record.temps_presence = 0.0
                record.temps_travail = 0.0

    def write(self, vals):
        res = super(IsSuiviTempsSaisie, self).write(vals)
        # Si des champs qui impactent les suivis du temps sont modifiés, mettre à jour les lignes
        if any(field in vals for field in ['heure_debut', 'heure_fin', 'temps_pose', 'heure_route', 'commentaire', 'panier', 'nuitee']):
            for record in self:
                for ligne in record.ligne_ids:
                    ligne._create_or_update_suivi_temps()
        return res

    @api.constrains('heure_debut', 'heure_fin')
    def _check_heures(self):
        for record in self:
            if record.heure_debut and record.heure_fin:
                if record.heure_debut >= record.heure_fin:
                    raise models.ValidationError("L'heure de fin doit être postérieure à l'heure de début.")

    @api.constrains('ligne_ids', 'commentaire')
    def _check_sav_commentaire(self):
        for record in self:
            # Vérifier si une ligne contient du SAV
            has_sav = any(ligne.type_travail == 'sav' for ligne in record.ligne_ids)
            if has_sav and not record.commentaire:
                raise models.ValidationError("Le commentaire est obligatoire lorsqu'une activité SAV est saisie. Veuillez indiquer les numéros des SAV concernés.")

    @api.constrains('ligne_ids', 'temps_pose', 'heure_route', 'temps_presence')
    def _check_durees_coherence(self):
        for record in self:
            # Vérifier qu'il y a au moins une ligne
            if not record.ligne_ids:
                raise models.ValidationError("Vous devez saisir au moins une ligne d'activité.")
            
            if record.temps_presence:
                # Calculer la somme des durées des lignes
                total_lignes = sum(record.ligne_ids.mapped('duree'))
                # Ajouter temps_pose et heure_route
                total_calcule = total_lignes + (record.temps_pose or 0.0) + (record.heure_route or 0.0)
                
                # Vérifier l'égalité (avec une tolérance de 0.01h pour les erreurs d'arrondi)
                if abs(total_calcule - record.temps_presence) > 0.01:
                    raise models.ValidationError(
                        f"Incohérence dans les durées :\n"
                        f"Total des activités : {total_lignes:.2f}h\n"
                        f"Temps de pose : {record.temps_pose or 0:.2f}h\n"
                        f"Heure de route : {record.heure_route or 0:.2f}h\n"
                        f"Total calculé : {total_calcule:.2f}h\n"
                        f"Temps de présence : {record.temps_presence:.2f}h\n\n"
                        f"Le total des durées des activités + temps de pose + heure de route doit être égal au temps de présence."
                    )

    _sql_constraints = [
        ('unique_utilisateur_date', 'UNIQUE(utilisateur_id, date)', 
         'Une saisie existe déjà pour cet utilisateur à cette date !')
    ]

    def action_voir_suivis_temps(self):
        """Ouvre la liste des suivis du temps liés à cette saisie"""
        self.ensure_one()
        
        # Récupérer les IDs des suivis du temps liés aux lignes
        suivi_temps_ids = self.ligne_ids.mapped('suivi_temps_id').ids
        
        return {
            'name': 'Suivis du temps',
            'type': 'ir.actions.act_window',
            'res_model': 'is.suivi.temps',
            'view_mode': 'list,form,calendar',
            'domain': [('id', 'in', suivi_temps_ids)],
            'context': {
                'default_utilisateur_id': self.utilisateur_id.id,
                'default_date': self.date,
            }
        }

    def copy(self, default=None):
        """Surcharge de la méthode copy pour incrémenter la date de 1 jour"""
        self.ensure_one()
        if default is None:
            default = {}
        
        # Calculer la date J+1
        from datetime import timedelta
        nouvelle_date = self.date + timedelta(days=1)
        
        # Vérifier si une saisie existe déjà pour cet utilisateur à cette date
        # Si oui, trouver la prochaine date disponible
        while self.env['is.suivi.temps.saisie'].search([
            ('utilisateur_id', '=', self.utilisateur_id.id),
            ('date', '=', nouvelle_date)
        ], limit=1):
            nouvelle_date += timedelta(days=1)
        
        # Mettre à jour le dictionnaire default avec la nouvelle date
        default.update({
            'date': nouvelle_date,
        })
        
        # Appeler la méthode parente pour créer la copie (avec copy=True, les lignes seront copiées)
        new_record = super(IsSuiviTempsSaisie, self).copy(default)
        
        return new_record

    def unlink(self):
        """Supprimer les IsSuiviTemps associés avant de supprimer la saisie"""
        # Récupérer tous les suivis du temps liés aux lignes
        suivis_to_delete = self.mapped('ligne_ids.suivi_temps_id')
        # Supprimer d'abord la saisie (cela supprimera les lignes en cascade)
        res = super(IsSuiviTempsSaisie, self).unlink()
        # Ensuite supprimer les suivis du temps avec sudo() pour avoir les droits
        if suivis_to_delete:
            suivis_to_delete.sudo().unlink()
        return res


class IsSuiviTempsSaisieLigne(models.Model):
    _name = 'is.suivi.temps.saisie.ligne'
    _description = 'Ligne de saisie du temps'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Séquence', default=10)
    saisie_id = fields.Many2one('is.suivi.temps.saisie', string='Saisie', required=True, ondelete='cascade', index=True)
    type_travail = fields.Selection(TYPE_TRAVAIL_SELECTION, string='Type de travail', required=True)
    centrale_id = fields.Many2one('is.centrale', string='Centrale', index=True)
    absence = fields.Selection([('recup', 'Récup'), ('cp', 'CP'), ('sans_solde', 'Sans solde'), ('conge', 'Congé'), ('evenement', 'Evenement'), ('repos', 'Repos')], string='Absence', index=True)
    duree = fields.Float(string='Durée', required=True, help='Durée en heures')
    suivi_temps_id = fields.Many2one('is.suivi.temps', string='Suivi du temps lié', readonly=True, index=True, copy=False)
    suivi_heure_debut = fields.Float(string='Suivi heure début', related='suivi_temps_id.heure_debut', readonly=True, store=False)
    suivi_heure_fin = fields.Float(string='Suivi heure fin', related='suivi_temps_id.heure_fin', readonly=True, store=False)

    @api.model_create_multi
    def create(self, vals_list):
        lignes = super(IsSuiviTempsSaisieLigne, self).create(vals_list)
        for ligne in lignes:
            ligne._create_or_update_suivi_temps()
        return lignes

    def write(self, vals):
        res = super(IsSuiviTempsSaisieLigne, self).write(vals)
        # Mettre à jour les suivis du temps liés si les champs importants changent
        if any(field in vals for field in ['type_travail', 'centrale_id', 'duree', 'absence']):
            for ligne in self:
                ligne._create_or_update_suivi_temps()
        return res

    def unlink(self):
        # Supprimer les suivis du temps liés avant de supprimer les lignes
        suivis_to_delete = self.mapped('suivi_temps_id')
        res = super(IsSuiviTempsSaisieLigne, self).unlink()
        if suivis_to_delete:
            suivis_to_delete.unlink()
        return res

    def _create_or_update_suivi_temps(self):
        """Crée ou met à jour l'enregistrement is.suivi.temps lié à cette ligne"""
        self.ensure_one()
        
        if not self.saisie_id or not self.duree:
            return
        
        saisie = self.saisie_id
        
        if not saisie.heure_debut:
            return
        
        # Récupérer toutes les lignes de la saisie dans l'ordre de séquence
        all_lignes = saisie.ligne_ids.sorted('sequence')
        
        # Calculer l'heure de début pour cette ligne
        # La première ligne commence à heure_debut, les suivantes à la fin de la précédente
        heure_debut_ligne = saisie.heure_debut
        for ligne in all_lignes:
            if ligne.id == self.id:
                break
            # Ajouter la durée de chaque ligne précédente
            heure_debut_ligne += ligne.duree
        
        # Calculer l'heure de fin pour cette ligne
        heure_fin_ligne = heure_debut_ligne + self.duree
        
        # Préparer les valeurs pour is.suivi.temps
        vals = {
            'utilisateur_id': saisie.utilisateur_id.id,
            'date': saisie.date,
            'heure_debut': heure_debut_ligne,
            'heure_fin': heure_fin_ligne,
            'type_travail': self.type_travail,
            'centrale_id': self.centrale_id.id if self.centrale_id else False,
            'absence': self.absence,
            'commentaire': saisie.commentaire,
            'panier': saisie.panier,
            'nuitee': saisie.nuitee,
        }
        
        # Créer ou mettre à jour l'enregistrement avec sudo()
        if self.suivi_temps_id:
            self.suivi_temps_id.sudo().write(vals)
        else:
            suivi = self.env['is.suivi.temps'].sudo().create(vals)
            self.suivi_temps_id = suivi.id
