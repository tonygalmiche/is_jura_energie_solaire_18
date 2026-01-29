# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import date
from dateutil.relativedelta import relativedelta


class IsMaintenance(models.Model):
    _name = 'is.maintenance'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Maintenance"
    _order = 'date_prevue desc, id desc'

    name = fields.Char("N° chrono", required=True, copy=False, readonly=True, default='Nouveau', tracking=True)
    centrale_id = fields.Many2one('is.centrale', string="Centrale", required=True, tracking=True)
    date_prevue = fields.Date("Date prévue", tracking=True, copy=False, required=True, default=fields.Date.today)
    couleur_alerte = fields.Selection(
        [
            ('vert', 'Vert'),
            ('jaune', 'Jaune'),
            ('orange', 'Orange'),
            ('rouge', 'Rouge'),
        ],
        string="Couleur alerte",
        compute='_compute_couleur_alerte',
        store=True,
        tracking=True, copy=False
    )
    nb_jours_avant = fields.Integer(
        "Nombre de jours avant maintenance",
        compute='_compute_nb_jours_avant',
        store=True,
        tracking=True, copy=False
    )
    nb_jours_retard = fields.Integer(
        "Nombre de jours de retard",
        compute='_compute_nb_jours_avant',
        store=True, copy=False
    )
    alerte_html = fields.Html(
        "Alerte",
        compute='_compute_alerte_html',
        sanitize=False,
    )
    annee = fields.Char("Année", compute='_compute_annee', store=True, tracking=True, copy=False)
    etat = fields.Selection(
        [
            ('pas_commence', 'Pas commencé'),
            ('en_cours', 'En cours'),
            ('termine', 'Terminé'),
        ],
        string="État",
        default='pas_commence',
        tracking=True,
        group_expand='_read_group_etat',
        copy=False,
        required=True
    )
    date_pas_commence = fields.Datetime("Date pas commencé", compute='_compute_dates_etat', store=True, readonly=True, tracking=True, copy=False)
    date_en_cours = fields.Datetime("Date en cours", compute='_compute_dates_etat', store=True, readonly=True, tracking=True, copy=False)
    date_termine = fields.Datetime("Date terminé", compute='_compute_dates_etat', store=True, readonly=True, tracking=True, copy=False)
    
    operation_hors_charge = fields.Selection(
        [
            ('a_planifier', 'A planifier'),
            ('planifie', 'Planifié'),
            ('fait', 'Fait'),
        ],
        string="Opération hors charge",
        tracking=True,
        default="a_planifier",
        required=True
    )
    operation_en_charge = fields.Selection(
        [
            ('a_planifier', 'A planifier'),
            ('planifie', 'Planifié'),
            ('fait', 'Fait'),
        ],
        string="Opération en charge",
        tracking=True,
        default='a_planifier',
        required=True
    )
    compte_rendu = fields.Selection(
        [
            ('a_planifier', 'A planifier'),
            ('planifie', 'Planifié'),
            ('fait', 'Fait'),
            ('envoye', 'Envoyé'),
        ],
        string="Compte-rendu",
        tracking=True,
        default='a_planifier',
        required=True
    )
    
    client_id = fields.Many2one('res.partner', related='centrale_id.client_id', string="Client", store=True, tracking=True)
    client_child_ids = fields.Many2many('res.partner', compute='_compute_client_child_ids', string="Contacts client")
    
    information_maintenance = fields.Text("Information maintenance", tracking=True)
    technicien_id = fields.Many2one('res.users', string="Technicien", tracking=True, required=True)
    pdf_signe_ids = fields.Many2many(
        'ir.attachment',
        'is_maintenance_pdf_signe_rel',
        'maintenance_id',
        'attachment_id',
        string="PDF signé par le client",
        tracking=True,
    )
    annexe_ids = fields.Many2many(
        'ir.attachment',
        'is_maintenance_annexe_rel',
        'maintenance_id',
        'attachment_id',
        string="Annexes",
    )

    # Champs pour les types de tâches
    type_tache_ids = fields.One2many('is.maintenance.type.tache', 'maintenance_id', string="Types de tâches")
    type_tache_count = fields.Integer("Nombre de tâches", compute='_compute_type_tache_count')

    # Champs pour les réunions
    calendar_event_ids = fields.One2many('calendar.event', 'is_maintenance_id', string='Réunions')
    meeting_display_date = fields.Date(compute="_compute_meeting_display")
    meeting_display_label = fields.Char(compute="_compute_meeting_display")

    @api.depends('calendar_event_ids', 'calendar_event_ids.start')
    def _compute_meeting_display(self):
        now = fields.Datetime.now()
        meeting_data = self.env['calendar.event'].sudo()._read_group([
            ('is_maintenance_id', 'in', self.ids),
        ], ['is_maintenance_id'], ['start:array_agg', 'start:max'])
        mapped_data = {
            maintenance: {
                'last_meeting_date': last_meeting_date,
                'next_meeting_date': min([dt for dt in meeting_start_dates if dt > now] or [False]),
            } for maintenance, meeting_start_dates, last_meeting_date in meeting_data
        }
        for maintenance in self:
            maintenance_meeting_info = mapped_data.get(maintenance)
            if not maintenance_meeting_info:
                maintenance.meeting_display_date = False
                maintenance.meeting_display_label = 'Pas de réunion'
            elif maintenance_meeting_info['next_meeting_date']:
                maintenance.meeting_display_date = maintenance_meeting_info['next_meeting_date']
                maintenance.meeting_display_label = 'Prochaine réunion'
            else:
                maintenance.meeting_display_date = maintenance_meeting_info['last_meeting_date']
                maintenance.meeting_display_label = 'Dernière réunion'

    def action_schedule_meeting(self, smart_calendar=True):
        """Ouvrir la vue calendrier pour planifier une réunion sur cette maintenance."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        partner_ids = self.env.user.partner_id.ids
        if self.client_id:
            partner_ids.append(self.client_id.id)
        current_maintenance_id = self.id
        # Nom de l'événement : Centrale (N° chrono)
        event_name = f"{self.centrale_id.name} ({self.name})" if self.centrale_id else self.name
        action['context'] = {
            'search_default_is_maintenance_id': current_maintenance_id,
            'default_is_maintenance_id': current_maintenance_id,
            'default_partner_id': self.client_id.id if self.client_id else False,
            'default_partner_ids': partner_ids,
            'default_name': event_name,
        }

        if current_maintenance_id and smart_calendar:
            mode, initial_date = self._get_maintenance_meeting_view_parameters()
            action['context'].update({'default_mode': mode, 'initial_date': initial_date})

        return action

    def _get_maintenance_meeting_view_parameters(self):
        """Retourner les paramètres les plus pertinents pour la vue calendrier."""
        self.ensure_one()
        meeting_results = self.env['calendar.event'].search([
            ('is_maintenance_id', '=', self.id),
            ('start', '>=', fields.Datetime.now()),
        ], order='start', limit=1)
        
        if meeting_results:
            return 'week', meeting_results.start.date()
        elif self.date_prevue:
            return 'week', self.date_prevue
        return 'week', False

    @api.depends('centrale_id.client_child_ids')
    def _compute_client_child_ids(self):
        for record in self:
            if record.centrale_id:
                record.client_child_ids = record.centrale_id.client_child_ids
            else:
                record.client_child_ids = False

    def action_open_maintenance(self):
        """Ouvrir la fiche de maintenance"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'is.maintenance',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('is.maintenance') or 'Nouveau'
        return super(IsMaintenance, self).create(vals_list)

    def write(self, vals):
        res = super(IsMaintenance, self).write(vals)
        # Si l'état passe à terminé, créer une nouvelle maintenance 1 an après
        if vals.get('etat') == 'termine':
            for record in self:
                if record.date_prevue and record.centrale_id:
                    # Vérifier qu'il n'existe pas déjà une maintenance après la date prévue
                    existing_maintenance = self.search([
                        ('centrale_id', '=', record.centrale_id.id),
                        ('date_prevue', '>', date.today() ),
                    ], limit=1)
                    if not existing_maintenance:
                        # Créer une nouvelle maintenance 1 an après la date du jour
                        new_date_prevue = date.today() + relativedelta(years=1)
                        self.create({
                            'centrale_id': record.centrale_id.id,
                            'date_prevue': new_date_prevue,
                            'technicien_id': record.technicien_id.id if record.technicien_id else self.env.user.id,
                        })
        return res

    @api.depends('etat')
    def _compute_dates_etat(self):
        for record in self:
            # Mémoriser la date lors du passage à chaque état (une seule fois)
            if record.etat == 'pas_commence' and not record.date_pas_commence:
                record.date_pas_commence = fields.Datetime.now()
            elif record.etat == 'en_cours' and not record.date_en_cours:
                record.date_en_cours = fields.Datetime.now()
            elif record.etat == 'termine' and not record.date_termine:
                record.date_termine = fields.Datetime.now()

    @api.depends('date_prevue', 'etat')
    def _compute_nb_jours_avant(self):
        today = date.today()
        for record in self:
            if record.etat == 'termine' or not record.date_prevue:
                record.nb_jours_avant = 0
                record.nb_jours_retard = 0
            else:
                delta = record.date_prevue - today
                record.nb_jours_avant = delta.days
                record.nb_jours_retard = abs(delta.days) if delta.days < 0 else 0

    @api.depends('nb_jours_avant', 'nb_jours_retard', 'couleur_alerte', 'date_prevue', 'etat')
    def _compute_alerte_html(self):
        for record in self:
            if record.etat == 'termine' or not record.date_prevue:
                record.alerte_html = ''
            else:
                # Définir la couleur de fond selon l'alerte
                couleurs = {
                    'vert': '#28a745',    # Vert
                    'jaune': '#ffc107',   # Jaune
                    'orange': '#fd7e14',  # Orange
                    'rouge': '#dc3545',   # Rouge
                }
                couleur_fond = couleurs.get(record.couleur_alerte, '#6c757d')
                couleur_texte = '#fff' if record.couleur_alerte != 'jaune' else '#000'
                
                # Texte à afficher
                if record.nb_jours_avant < 0:
                    texte = f"Retard {record.nb_jours_retard}j"
                elif record.nb_jours_avant == 0:
                    texte = "Aujourd'hui"
                else:
                    texte = f"Dans {record.nb_jours_avant}j"
                
                record.alerte_html = f'''<span style="background-color: {couleur_fond}; color: {couleur_texte}; padding: 2px 6px; border-radius: 3px; font-weight: bold; font-size: 11px; display: inline-block; line-height: 1.2;">{texte}</span>'''

    @api.depends('date_prevue', 'etat')
    def _compute_couleur_alerte(self):
        today = date.today()
        for record in self:
            if record.etat == 'termine':
                record.couleur_alerte = 'vert'
            elif not record.date_prevue:
                record.couleur_alerte = False
            else:
                delta = record.date_prevue - today
                jours = delta.days
                
                if jours < 0:
                    record.couleur_alerte = 'rouge'  # En retard
                elif jours <= 7:
                    record.couleur_alerte = 'orange'  # 1 semaine avant
                elif jours <= 30:
                    record.couleur_alerte = 'jaune'  # Moins d'un mois
                else:
                    record.couleur_alerte = 'vert'  # Plus d'un mois

    @api.depends('date_prevue')
    def _compute_annee(self):
        for record in self:
            if record.date_prevue:
                record.annee = str(record.date_prevue.year)
            else:
                record.annee = False

    @api.model
    def _read_group_etat(self, stages, domain):
        mylist = []
        for line in self._fields['etat'].selection:
            mylist.append(line[0])
        return mylist

    @api.model
    def cron_update_couleur_alerte(self):
        """Cron pour actualiser la couleur d'alerte et le nombre de jours chaque nuit"""
        maintenances = self.search([])
        maintenances._compute_couleur_alerte()
        maintenances._compute_nb_jours_avant()

    def action_creer_taches_depuis_modeles(self):
        """Créer les types de tâches pour cette maintenance à partir des modèles"""
        self.ensure_one()
        centrale = self.centrale_id
        # Récupérer tous les modèles (types de tâches sans maintenance associée)
        modeles = self.env['is.maintenance.type.tache'].search([('maintenance_id', '=', False)])
        for modele in modeles:
            # Vérifier si c'est un type Coffret DC
            if modele.is_type_coffret_dc:
                # Ne créer que si coffret_dc est coché sur la centrale
                if not centrale.coffret_dc:
                    continue
            
            # Vérifier si c'est un type Onduleur
            if modele.is_type_onduleur:
                # Créer un type de tâche par onduleur de la centrale
                for numero, onduleur in enumerate(centrale.onduleur_ids, start=1):
                    nouveau_type = self.env['is.maintenance.type.tache'].create({
                        'name': "%s %s" % (modele.name, numero),
                        'sequence': modele.sequence,
                        'maintenance_id': self.id,
                        'numero_ordre': numero,
                        'onduleur_id': onduleur.id,
                    })
                    # Copier les tâches associées
                    for tache in modele.tache_ids:
                        self.env['is.maintenance.tache'].create({
                            'type_tache_id': nouveau_type.id,
                            'sequence': tache.sequence,
                            'name': tache.name,
                        })
                continue
            
            # Vérifier si c'est un type Champs photovoltaïque
            if modele.is_type_champs_photovoltaique:
                # Créer autant de types de tâches que nb_champs_solaire
                nb_champs = centrale.nb_champs_solaire or 0
                for numero in range(1, nb_champs + 1):
                    nouveau_type = self.env['is.maintenance.type.tache'].create({
                        'name': "%s %s" % (modele.name, numero),
                        'sequence': modele.sequence,
                        'maintenance_id': self.id,
                        'numero_ordre': numero,
                    })
                    # Copier les tâches associées
                    for tache in modele.tache_ids:
                        self.env['is.maintenance.tache'].create({
                            'type_tache_id': nouveau_type.id,
                            'sequence': tache.sequence,
                            'name': tache.name,
                        })
            else:
                # Copier le type de tâche normalement
                nouveau_type = self.env['is.maintenance.type.tache'].create({
                    'name': modele.name,
                    'sequence': modele.sequence,
                    'maintenance_id': self.id,
                })
                # Copier les tâches associées
                for tache in modele.tache_ids:
                    self.env['is.maintenance.tache'].create({
                        'type_tache_id': nouveau_type.id,
                        'sequence': tache.sequence,
                        'name': tache.name,
                    })
        return True

    def _compute_type_tache_count(self):
        for record in self:
            record.type_tache_count = len(record.type_tache_ids)

    def action_view_taches(self):
        """Ouvrir la liste des types de tâches liées à cette maintenance"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tâches de maintenance',
            'res_model': 'is.maintenance.type.tache',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('is_jura_energie_solaire_18.view_is_maintenance_type_tache_tree').id, 'list'),
                (self.env.ref('is_jura_energie_solaire_18.view_is_maintenance_type_tache_form').id, 'form'),
            ],
            'domain': [('maintenance_id', '=', self.id)],
            'context': {'default_maintenance_id': self.id},
        }
