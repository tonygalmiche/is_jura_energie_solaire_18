# -*- coding: utf-8 -*-
from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import pytz

# Liste partagée des secteurs
SECTEUR_SELECTION = [
    ('gp', 'GP'),
    ('re', 'RE'),
    ('th', 'TH'),
    ('si', 'SI'),
    ('irve', 'IRVE'),
]


class IsCentraleTypeInstallation(models.Model):
    _name = 'is.centrale.type.installation'
    _description = "Type d'installation"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class IsCentraleTypeCapteur(models.Model):
    _name = 'is.centrale.type.capteur'
    _description = "Type de capteur"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class IsCentraleTypeBallonSanitaire(models.Model):
    _name = 'is.centrale.type.ballon.sanitaire'
    _description = "Type de ballon sanitaire"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class IsCentraleTypeBallonTampon(models.Model):
    _name = 'is.centrale.type.ballon.tampon'
    _description = "Type de ballon tampon"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class IsCentraleArbreHydraulique(models.Model):
    _name = 'is.centrale.arbre.hydraulique'
    _description = "Arbre hydraulique"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class IsCentraleRegulation(models.Model):
    _name = 'is.centrale.regulation'
    _description = "Régulation"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class IsCentraleAppoint(models.Model):
    _name = 'is.centrale.appoint'
    _description = "Appoint"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class IsCentraleMarque(models.Model):
    _name = 'is.centrale.marque'
    _description = "Marque"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class IsCentraleAffaire(models.Model):
    _name='is.centrale.affaire'
    _description = "Affaire des centrales"
    _order='name,id'

    name = fields.Char("Affaire")
    centrale_ids = fields.One2many('is.centrale', 'affaire_id', string="Centrales", readonly=True)
    puissance_panneau_totale = fields.Float("Puissance totale (kWc)", compute='_compute_puissance_panneau_totale', store=True)

    #euro         = fields.Float("€/kWc", compute='_compute_tarifs', store=True, digits=(10, 0))
    euro_par_kwc = fields.Float("€/kWc", compute='_compute_tarifs', store=True, digits=(10, 1))

    #forfait = fields.Integer("Forfait", compute='_compute_tarifs', store=True)
    formule_id = fields.Many2one('is.centrale.formule', string="Formule appliquée", compute='_compute_tarifs', store=True)

    @api.depends('puissance_panneau_totale')
    def _compute_tarifs(self):
        for record in self:
            formule, euro_ht, euro_par_kwc = self.env['is.centrale.formule'].calculer_pour_kwc(record.puissance_panneau_totale)
            record.euro_par_kwc = euro_par_kwc
            record.formule_id = formule.id if formule else False

    @api.depends('centrale_ids.puissance_panneau_totale')
    def _compute_puissance_panneau_totale(self):
        for record in self:
            record.puissance_panneau_totale = sum(record.centrale_ids.mapped('puissance_panneau_totale'))

    def action_view_centrales(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Centrales',
            'res_model': 'is.centrale',
            'view_mode': 'list,form',
            'domain': [('affaire_id', '=', self.id)],
            'context': {'default_affaire_id': self.id},
        }



class IsCentraleFormule(models.Model):
    _name='is.centrale.formule'
    _description = "Formule des centrales"
    _rec_name = "limite_kwc"
    _order='limite_kwc,id'

    limite_kwc   = fields.Integer("Limite (<=)(kWc)", required=True)
    formule      = fields.Char("Formule")
    euro         = fields.Float("€"    , compute='_compute_euro_par_kwc', store=True, readonly=True, digits=(10, 0))
    euro_par_kwc = fields.Float("€/kWc", compute='_compute_euro_par_kwc', store=True, readonly=True, digits=(10, 1))
    commentaire  = fields.Char("Commentaire")

    @api.model
    def get_formule_pour_kwc(self, kwc):
        formule = self.search([('limite_kwc', '>=', kwc)], order='limite_kwc asc', limit=1)
        if not formule:
            formule = self.search([], order='limite_kwc desc', limit=1)
        return formule

    @api.model
    def calculer_pour_kwc(self, kwc):
        formule = self.get_formule_pour_kwc(kwc)
        euro_ht = 0.0
        euro_par_kwc = 0.0
        if formule and formule.formule and kwc > 0:
            try:
                formule_calc = formule.formule.replace(',', '.').replace('x', str(kwc))
                euro_ht = float(eval(formule_calc, {"__builtins__": {}}, {}))
                euro_par_kwc = euro_ht / kwc
            except Exception:
                pass
        return formule, euro_ht, euro_par_kwc

    @api.model_create_multi
    def create(self, vals_list):
        records = super(IsCentraleFormule, self).create(vals_list)
        self.env['is.centrale.affaire'].search([])._compute_tarifs()
        return records

    def write(self, vals):
        res = super(IsCentraleFormule, self).write(vals)
        self.env['is.centrale.affaire'].search([])._compute_tarifs()
        return res

    @api.depends('limite_kwc', 'formule')
    def _compute_euro_par_kwc(self):
        for obj in self:
            result = 0.0
            if obj.formule:
                try:
                    # Remplacer 'x' par la valeur de limite_kwc dans la formule
                    kwc_value = obj.limite_kwc if obj.limite_kwc else 1  # Éviter division par zéro
                    # Remplacer les virgules par des points pour le format numérique
                    formule_calc = obj.formule.replace(',', '.').replace('x', str(kwc_value))
                    # Évaluer la formule de manière sécurisée
                    result = float(eval(formule_calc, {"__builtins__": {}}, {}))
                except Exception as e:
                    result = 0.0

            obj.euro = result
            euro_par_kwc = 0
            if  obj.limite_kwc>0:
                euro_par_kwc = obj.euro / obj.limite_kwc
            obj.euro_par_kwc = euro_par_kwc


class IsCentraleFormuleResultat(models.Model):
    _name = 'is.centrale.formule.resultat'
    _description = "Résultats des formules"
    _order = 'kwc'

    kwc          = fields.Integer("kWc")
    euro_ht      = fields.Float("€(HT)", digits=(10, 2))
    euro_par_kwc = fields.Float("€/kWc", digits=(10, 2))

    @api.model
    def action_generer_resultats(self):
        # Supprimer les fiches existantes
        self.search([]).unlink()

        vals_list = []
        for kwc in range(1, 1001):
            formule, euro_ht, euro_par_kwc = self.env['is.centrale.formule'].calculer_pour_kwc(kwc)
            vals_list.append({
                'kwc': kwc,
                'euro_ht': euro_ht,
                'euro_par_kwc': euro_par_kwc,
            })

        self.create(vals_list)

        graph_view = self.env.ref('is_jura_energie_solaire_18.view_is_centrale_formule_resultat_graph_euro_ht', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'name': '€(HT) par kWc',
            'res_model': 'is.centrale.formule.resultat',
            'view_mode': 'graph,list',
            'views': [(graph_view.id if graph_view else False, 'graph'), (False, 'list')],
        }


class IsCentralePanneau(models.Model):
    _name='is.centrale.panneau'
    _description = "Panneaux des centrales"
    _order='sequence,id'

    centrale_id       = fields.Many2one('is.centrale', 'Centrale', required=True, ondelete='cascade')
    sequence          = fields.Integer("Ordre")
    panneau_id        = fields.Many2one('product.product', string="Panneau")
    quantite          = fields.Integer("Quantité")
    puissance_panneau = fields.Integer('Puissance panneau (W)', compute='_compute', store=True, readonly=True)
    puissance_totale  = fields.Float('Puissance totale (kW)' , compute='_compute', store=True, readonly=True, digits=(3, 2))
 
    @api.depends('panneau_id','panneau_id.product_tmpl_id.is_puissance_w','quantite','puissance_panneau')
    def _compute(self):
        for obj in self:
            puissance_panneau = 0
            if obj.panneau_id:
                puissance_panneau = obj.panneau_id.product_tmpl_id.is_puissance_w
            obj.puissance_panneau = puissance_panneau
            obj.puissance_totale  = puissance_panneau * obj.quantite / 1000




class IsCentraleOnduleur(models.Model):
    _name='is.centrale.onduleur'
    _description = "Onduleurs des centrales"
    _order='sequence,id'
    _rec_name = "onduleur_id"

    centrale_id        = fields.Many2one('is.centrale', 'Centrale', required=True, ondelete='cascade')
    sequence           = fields.Integer("Ordre")
    onduleur_id        = fields.Many2one('product.product', string="Onduleur")
    quantite           = fields.Integer("Quantité", default=1)
    puissance_onduleur = fields.Float('Puissance onduleur (kVA)', compute='_compute', store=True, readonly=True)
    puissance_totale   = fields.Float('Puissance totale (kVA)'  , compute='_compute', store=True, readonly=True)
    numero_serie       = fields.Char("Numéro de série")
    date_debut_garantie = fields.Date("Date début garantie")
    annee_garantie     = fields.Char("Année de garantie", compute='_compute_annee_garantie', store=True, readonly=True)
    garantie_ids       = fields.Many2many('ir.attachment', 'is_centrale_onduleur_garantie_rel', 'onduleur_id', 'attachment_id', string="Papiers de garantie")
 
    @api.depends('onduleur_id','onduleur_id.product_tmpl_id.is_puissance_kva','quantite','puissance_onduleur')
    def _compute(self):
        for obj in self:
            puissance_onduleur = 0
            if obj.onduleur_id:
                puissance_onduleur = obj.onduleur_id.product_tmpl_id.is_puissance_kva
            obj.puissance_onduleur = puissance_onduleur
            obj.puissance_totale  = puissance_onduleur * obj.quantite 

    @api.depends('date_debut_garantie')
    def _compute_annee_garantie(self):
        for obj in self:
            if obj.date_debut_garantie:
                obj.annee_garantie = str(obj.date_debut_garantie.year)
            else:
                obj.annee_garantie = False 


class IsCentraleCoffret(models.Model):
    _name='is.centrale.coffret'
    _description = "Coffrets des centrales"
    _order='sequence,id'

    centrale_id        = fields.Many2one('is.centrale', 'Centrale', required=True, ondelete='cascade')
    sequence           = fields.Integer("Ordre")
    coffret_id         = fields.Many2one('product.product', string="Protection électrique")
    quantite           = fields.Integer("Quantité")


class IsCentraleOptimiseur(models.Model):
    _name='is.centrale.optimiseur'
    _description = "Optimiseurs des centrales"
    _order='sequence,id'

    centrale_id        = fields.Many2one('is.centrale', 'Centrale', required=True, ondelete='cascade')
    sequence           = fields.Integer("Ordre")
    optimiseur_id      = fields.Many2one('product.product', string="Optimiseur")
    quantite           = fields.Integer("Quantité")
 

class IsCentraleSystemeIntegration(models.Model):
    _name='is.centrale.systeme.integration'
    _description = "Système d'intégration des centrales"
    _order='sequence,id'

    centrale_id              = fields.Many2one('is.centrale', 'Centrale', required=True, ondelete='cascade')
    sequence                 = fields.Integer("Ordre")
    systeme_integration_id   = fields.Many2one('product.product', string="Système d'intégration")
    quantite                 = fields.Integer("Quantité")


class IsCentraleRaccordementElectrique(models.Model):
    _name = 'is.centrale.raccordement.electrique'
    _description = "Raccordement électrique"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class IsCentraleTypePose(models.Model):
    _name = 'is.centrale.type.pose'
    _description = "Type de pose"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class IsCentraleCableElectrique(models.Model):
    _name = 'is.centrale.cable.electrique'
    _description = "Câble électrique des centrales"
    _order = 'sequence,id'

    centrale_id      = fields.Many2one('is.centrale', 'Centrale', required=True, ondelete='cascade')
    sequence         = fields.Integer("Ordre")
    depart_id        = fields.Many2one('is.centrale.raccordement.electrique', string="Départ")
    fin_id           = fields.Many2one('is.centrale.raccordement.electrique', string="Fin")
    type_cable_id    = fields.Many2one('product.product', string="Type de câble")
    longueur         = fields.Float("Longueur (m)", digits=(10, 1))
    type_pose_ids    = fields.Many2many(
        'is.centrale.type.pose',
        'is_centrale_cable_type_pose_rel',
        'cable_id',
        'type_pose_id',
        string="Type de pose",
    )


class IsCentraleAutre(models.Model):
    _name = 'is.centrale.autre'
    _description = "Autres équipements des centrales"
    _order = 'sequence,id'

    centrale_id  = fields.Many2one('is.centrale', 'Centrale', required=True, ondelete='cascade')
    sequence     = fields.Integer("Ordre")
    produit_id   = fields.Many2one('product.product', string="Produit")
    quantite     = fields.Integer("Quantité")


class IsCentrale(models.Model):
    _name='is.centrale'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Centrale"
    _order='name'

    name                     = fields.Char("Nom", size=40, required=True, tracking=True)

 
    secteur = fields.Selection(
        SECTEUR_SELECTION,
        string="Secteur",
        tracking=True,
    )
    type_installation_ids = fields.Many2many(
        'is.centrale.type.installation',
        'is_centrale_type_installation_rel',
        'centrale_id',
        'type_installation_id',
        string="Type d'installation",
        tracking=True,
    )

    # Champs Capteur (secteur TH)
    type_capteur_ids = fields.Many2many(
        'is.centrale.type.capteur',
        'is_centrale_type_capteur_rel',
        'centrale_id',
        'type_capteur_id',
        string="Type de capteur",
    )
    surface_capteur = fields.Float("Surface capteur (m²)", digits=(10, 2))

    # Champs Système hydraulique (secteur TH)
    type_ballon_sanitaire_ids = fields.Many2many(
        'is.centrale.type.ballon.sanitaire',
        'is_centrale_type_ballon_sanitaire_rel',
        'centrale_id',
        'type_ballon_sanitaire_id',
        string="Type ballon sanitaire",
    )
    volume_ballon_sanitaire = fields.Float("Volume ballon sanitaire", digits=(10, 2))
    type_ballon_tampon_ids = fields.Many2many(
        'is.centrale.type.ballon.tampon',
        'is_centrale_type_ballon_tampon_rel',
        'centrale_id',
        'type_ballon_tampon_id',
        string="Type ballon tampon",
    )
    volume_ballon_tampon = fields.Float("Volume ballon tampon", digits=(10, 2))
    arbre_hydraulique_ids = fields.Many2many(
        'is.centrale.arbre.hydraulique',
        'is_centrale_arbre_hydraulique_rel',
        'centrale_id',
        'arbre_hydraulique_id',
        string="Arbre hydraulique",
    )
    regulation_ids = fields.Many2many(
        'is.centrale.regulation',
        'is_centrale_regulation_rel',
        'centrale_id',
        'regulation_id',
        string="Régulation",
    )

    # Champs Appoint (secteur TH)
    appoint_ids = fields.Many2many(
        'is.centrale.appoint',
        'is_centrale_appoint_rel',
        'centrale_id',
        'appoint_id',
        string="Appoint",
    )
    marque_ids = fields.Many2many(
        'is.centrale.marque',
        'is_centrale_marque_rel',
        'centrale_id',
        'marque_id',
        string="Marque",
    )
    appoint_modele = fields.Char("Modèle")
    appoint_numero_serie = fields.Char("Numéro de série")
    appoint_puissance_kw = fields.Float("Puissance (kW)", digits=(10, 2))
    appoint_commentaire = fields.Text("Commentaire")
    appoint_photo = fields.Binary("Photo appoint")

    # Champs PV de réception (secteur TH)
    pv_date = fields.Date("Date PV")
    pv_attachment_ids = fields.Many2many(
        'ir.attachment',
        'is_centrale_pv_attachment_rel',
        'centrale_id',
        'attachment_id',
        string="Pièces jointes PV",
    )

    das = fields.Selection(
        [
            ('gp_agri'        , 'Agri'),
            ('gp_ci'          , 'C&I'),
            ('gp_collectivite', 'Collectivité'),
        ],
        string="DAS",
        tracking=True,
    )
    affaire_id               = fields.Many2one('is.centrale.affaire', string="Affaire", tracking=True)
    affaire_puissance_panneau_totale = fields.Float(related='affaire_id.puissance_panneau_totale', string="Puissance totale de l'affaire", store=True, tracking=True)
    affaire_euro_par_kwc = fields.Float(related='affaire_id.euro_par_kwc', string="€/kWc", store=True, tracking=True)
    #affaire_forfait = fields.Integer(related='affaire_id.forfait', string="Forfait", store=True, tracking=True)
    affaire_formule_id = fields.Many2one(related='affaire_id.formule_id', string="Formule appliquée", store=True, tracking=True)
    montant_maintenance = fields.Float(
        string="Montant maintenance",
        compute="_compute_montant_maintenance",
        store=True,
    )
    maintenance_statut = fields.Selection(
        [
            ('en_attente', 'En Attente'),
            ('envoye', 'Envoyé'),
            ('signe', 'Signé'),
            ('refuse', 'Refusé'),
        ],
        string="Maintenance État",
        tracking=True,
        group_expand='_read_group_maintenance_statut',
    )

    maintenance_date_signature = fields.Date("Date de Signature", tracking=True)
    contrat_signe_ids = fields.Many2many('ir.attachment', 'is_centrale_contrat_signe_rel', 'centrale_id', 'attachment_id', string="Contrat de maintenance signé")
    maintenance_ids = fields.One2many('is.maintenance', 'centrale_id', string="Maintenances")
    projet_id                = fields.Many2one('project.project', string="Projet")
    localisation             = fields.Char("Localisation", tracking=True)
    localisation_google_maps_url = fields.Char("URL Google Maps", compute='_compute_localisation_google_maps_url', readonly=True)
    adresse                  = fields.Char("Adresse", size=60, tracking=True)
    client_id                = fields.Many2one('res.partner', string="Client", tracking=True)
    client_child_ids = fields.One2many(related="client_id.child_ids")
    lead_ids = fields.One2many('crm.lead', 'is_centrale_id', string="Opportunités")
    sav_ids = fields.One2many('is.sav', 'centrale_id', string="SAVs", tracking=True)
    purchase_line_ids = fields.One2many('purchase.order.line', 'is_centrale_id', string="Lignes d'achats")
    purchase_order_count  = fields.Integer(compute='_compute_purchase_order_count')
    calendar_event_ids    = fields.One2many('calendar.event', 'is_centrale_id', string='Réunion')
    meeting_display_date  = fields.Date(compute="_compute_meeting_display")
    meeting_display_label = fields.Char(compute="_compute_meeting_display")
    puissance_onduleur_demandee = fields.Float(string="Puissance onduleurs demandée (kVA)")
    puissance_panneau_demandee  = fields.Float(string="Puissance panneaux demandée (kWc)")
    puissance_onduleur_totale = fields.Float(
        string="Puissance des onduleurs (kVA)",
        compute="_compute_puissance_onduleur_totale",
        store=True,
        readonly=True,
    )
    puissance_panneau_totale = fields.Float(
        string="Puissance des panneaux (kWc)",
        compute="_compute_puissance_panneau_totale",
        store=True,
        readonly=True,
        digits=(3, 2),
    )

    # Onglet "DP/PC"
    is_afficher_administratif = fields.Boolean("Afficher l'administratif", default=True)
    dp_etat = fields.Selection(
        [
            ('a_faire'   , 'A faire'),
            ('depose'    , 'Déposé'),
            ('completude', 'Complétude'),
            ('obtenu'    , 'Obtenu'),
        ],
        string="DP État",
        tracking=True,
        group_expand='_read_group_dp_etat',
    )
    dp_depose       = fields.Date("DP Déposé", tracking=True)
    dp_obtention    = fields.Date("DP Obtention", tracking=True)
    dp_informations = fields.Text("DP/PC Informations", tracking=True)
    dp_attachment_ids = fields.Many2many(
        'ir.attachment',
        'is_centrale_dp_attachment_rel',
        'centrale_id',
        'attachment_id',
        string="Pièces jointes DP",
    )

    # Onglet "PTF"
    ptf_etat = fields.Selection(
        [
            ('a_faire'   , 'A faire'),
            ('depose'    , 'Déposé'),
            ('completude', 'Complétude'),
            ('obtenu'    , 'Obtenu'),
        ],
        string="PTF État",
        tracking=True,
        group_expand='_read_group_ptf_etat',
    )
    ptf_reference    = fields.Char("PTF Référence", tracking=True)
    ptf_depose       = fields.Date("PTF Déposé", tracking=True)
    ptf_obtention    = fields.Date("PTF Obtention", tracking=True)
    ptf_informations = fields.Text("PTF Informations", tracking=True)

    # Onglet "CRD"
    crd_etat = fields.Selection(
        [
            ('en_attente', 'En attente'),
            ('recu'      , 'Reçu'),
            ('traite'    , 'Traité'),
            ('signe'     , 'Signé'),
        ],
        string="CRD État",
        tracking=True,
        group_expand='_read_group_crd_etat',
    )
    crd_recu         = fields.Date("Date limite CRD", tracking=True)
    crd_signature    = fields.Date("CRD Signature", tracking=True)
    crd_informations = fields.Text("CRD Informations", tracking=True)
    crd_signe_ids    = fields.Many2many('ir.attachment', 'is_centrale_crd_signe_rel', 'centrale_id', 'attachment_id', string="CRD signé")


    # Onglet "CARD-I"
    cardi_etat = fields.Selection(
        [
            ('a_faire'      , 'A faire'),
            ('pret'         , 'Prêt'),
            ('envoye_client', 'Envoyé chez Client'),
            ('envoye_enedis', 'Envoyé Enedis'),
            ('obtenu'       , 'Obtenu'),
        ],
        string="CARD-I État",
        tracking=True,
        group_expand='_read_group_cardi_etat',
    )
    cardi_depose       = fields.Date("CARD-I Déposé", tracking=True)
    cardi_obtenu       = fields.Date("CARD-I Obtenu", tracking=True)
    cardi_informations = fields.Text("CARD-I Informations", tracking=True)
    cardi_signe_ids    = fields.Many2many('ir.attachment', 'is_centrale_cardi_signe_rel', 'centrale_id', 'attachment_id', string="CARD-I signé")


    # Onglet "Socotec"
    socotec_etat = fields.Selection(
        [
            ('en_attente', 'En attente'),
            ('a_prevoir' , 'A prévoir'),
            ('planifie'  , 'Planifié'),
        ],
        string="Socotec État",
        tracking=True,
        group_expand='_read_group_socotec_etat',
    )
    socotec_controle     = fields.Date("Socotec Contrôle", tracking=True)
    socotec_informations = fields.Text("Socotec Informations", tracking=True)
    socotec_conformite_electrique_ids = fields.Many2many('ir.attachment', 'is_centrale_socotec_conformite_rel', 'centrale_id', 'attachment_id', string="Conformité électrique")

    # Onglet "Consuel"
    consuel_etat = fields.Selection(
        [
            ('a_faire'   , 'A faire'),
            ('depose'    , 'Déposé'),
            ('completude', 'Complétude'),
            ('obtenu'    , 'Obtenu'),
        ],
        string="Consuel État",
        tracking=True,
        group_expand='_read_group_consuel_etat',
    )
    consuel_depose       = fields.Date("Consuel Déposé", tracking=True)
    consuel_obtention    = fields.Date("Consuel Obtention", tracking=True)
    consuel_informations = fields.Text("Consuel Informations", tracking=True)
    consuel_attachment_ids = fields.Many2many('ir.attachment', 'is_centrale_consuel_attachment_rel', 'centrale_id', 'attachment_id', string="Consuel")

    # Onglet "Mise en service"
    mes_demande      = fields.Date("MES Demandé", tracking=True)
    mes_realise      = fields.Date("MES Réalisé", tracking=True)
    mes_informations = fields.Text("MES Informations", tracking=True)

    # Onglet "S21"
    s21_etat = fields.Selection(
        [
            ('a_prevoir', 'A prévoir'),
            ('en_cours' , 'En cours'),
            ('pret'     , 'Prêt'),
            ('envoye'   , 'Envoyé'),
        ],
        string="S21 État",
        tracking=True,
        group_expand='_read_group_s21_etat',
    )
    s21_envoye       = fields.Date("S21 Envoyé", tracking=True)
    s21_obtenu       = fields.Date("S21 Obtenu", tracking=True)
    s21_informations = fields.Text("S21 Informations", tracking=True)
    s21_attestation_conformite_ids = fields.Many2many('ir.attachment', 'is_centrale_s21_attestation_rel', 'centrale_id', 'attachment_id', string="Attestation de conformité")

    # Onglet "EDF AO"
    edf_identifiant  = fields.Char("Identifiant client", tracking=True)
    edf_mail         = fields.Char("Mail", tracking=True)
    edf_mot_de_passe = fields.Char("Mot de passe", tracking=True)
    edf_num_bta      = fields.Char("N°BTA", tracking=True)
    edf_etat = fields.Selection(
        [
            ('en_attente'     , 'En attente'),
            ('a_completer'    , 'A compléter'),
            ('en_verification', 'En vérification'),
            ('signe'          , 'Signé'),
        ],
        string="EDF AO État",
        tracking=True,
        group_expand='_read_group_edf_etat',
    )
    edf_informations = fields.Text("EDF AO Informations", tracking=True)

    # Onglet "Informations techniques"
    panneau_ids  = fields.One2many('is.centrale.panneau' , 'centrale_id', 'Panneaux')
    onduleur_ids = fields.One2many('is.centrale.onduleur', 'centrale_id', 'Onduleurs')
    bridage_onduleur = fields.Integer("Bridage onduleur (kVA)", tracking=True)
    coffret_ids  = fields.One2many('is.centrale.coffret' , 'centrale_id', 'Protections électriques')
    type_communication = fields.Selection(
        [
            ('wifi'      , 'Wi-Fi'),
            ('cellulaire', 'Cellulaire'),
            ('rj45'      , 'RJ45'),
        ],
        string="Type de communication",
        tracking=True,
    )
    nature_entrale = fields.Selection(
        [
            ('revente'         , 'Revente'),
            ('autoconsommation', 'Autoconsommation'),
        ],
        string="Nature de la centrale",
        tracking=True,
    )
    prm = fields.Char("PRM", tracking=True)
    loget = fields.Selection(
        [
            ('tarif_jaune', 'Tarif Jaune'),
            ('tarif_bleu' , 'Tarif Bleu'),
            ('tarif_vert' , 'Tarif Vert'),
        ],
        string="Loget",
        tracking=True,
    )
    coffret_dc          = fields.Boolean("Coffret DC", default=False, tracking=True)
    nb_champs_solaire   = fields.Integer("Nombre de champs solaire", tracking=True)
    presence_optimiseur = fields.Boolean("Présence d’optimiseur", default=False, tracking=True)
    optimiseur_ids      = fields.One2many('is.centrale.optimiseur' , 'centrale_id', 'Optimiseurs')
    systeme_integration_ids = fields.One2many('is.centrale.systeme.integration', 'centrale_id', "Système d'intégration")
    cable_electrique_ids    = fields.One2many('is.centrale.cable.electrique', 'centrale_id', "Câbles électriques")
    autre_ids               = fields.One2many('is.centrale.autre', 'centrale_id', "Autres")

    # Onglet "Plans d'exécution"
    plan_calepinage_ids          = fields.Many2many('ir.attachment', 'is_centrale_plan_calepinage_rel',       'centrale_id', 'attachment_id', string="Plan de calepinage")
    plan_chaines_ids             = fields.Many2many('ir.attachment', 'is_centrale_plan_chaines_rel',          'centrale_id', 'attachment_id', string="Plan des chaînes")
    plan_dimensionnement_ids     = fields.Many2many('ir.attachment', 'is_centrale_plan_dimensionnement_rel',  'centrale_id', 'attachment_id', string="Dimensionnement onduleur")
    plan_raccordement_ids        = fields.Many2many('ir.attachment', 'is_centrale_plan_raccordement_rel',     'centrale_id', 'attachment_id', string="Raccordement Électrique")
    plan_schema_unifilaire_ids   = fields.Many2many('ir.attachment', 'is_centrale_plan_schema_unifilaire_rel','centrale_id', 'attachment_id', string="Schéma Unifilaire")
    plan_securite_ids            = fields.Many2many('ir.attachment', 'is_centrale_plan_securite_rel',        'centrale_id', 'attachment_id', string="Plan de sécurité")
    plan_masse_ids               = fields.Many2many('ir.attachment', 'is_centrale_plan_masse_rel',           'centrale_id', 'attachment_id', string="Plan de masse")
    plan_note_calculs_ids        = fields.Many2many('ir.attachment', 'is_centrale_plan_note_calculs_rel',    'centrale_id', 'attachment_id', string="Note de calculs Électrique")
    plan_autres_ids              = fields.Many2many('ir.attachment', 'is_centrale_plan_autres_rel',          'centrale_id', 'attachment_id', string="Autres")


    @api.onchange('secteur')
    def onchange_secteur(self):
        for obj in self:
            if obj.secteur == 're':
                obj.loget = 'tarif_bleu'

    @api.onchange('crd_etat')
    def onchange_crd_etat(self):
        for obj in self:
            print(obj,obj.crd_etat)
            if obj.crd_etat=='signe':
                obj.cardi_etat='a_faire'


    @api.depends('affaire_euro_par_kwc', 'puissance_panneau_totale')
    def _compute_montant_maintenance(self):
        for record in self:
            record.montant_maintenance = record.affaire_euro_par_kwc * record.puissance_panneau_totale

    @api.depends('onduleur_ids.puissance_totale', 'bridage_onduleur')
    def _compute_puissance_onduleur_totale(self):
        for record in self:
            if record.bridage_onduleur:
                record.puissance_onduleur_totale = record.bridage_onduleur
            else:
                record.puissance_onduleur_totale = sum(
                    onduleur.puissance_totale for onduleur in record.onduleur_ids
                )

    @api.depends('panneau_ids.puissance_totale')
    def _compute_puissance_panneau_totale(self):
        for record in self:
            record.puissance_panneau_totale = sum(
                panneau.puissance_totale for panneau in record.panneau_ids
            )

    @api.depends('localisation')
    def _compute_localisation_google_maps_url(self):
        for record in self:
            if record.localisation:
                # Format attendu : "latitude,longitude" (exemple: "46.918792,5.741772")
                record.localisation_google_maps_url = f"https://www.google.com/maps/search/?api=1&query={record.localisation}"
            else:
                record.localisation_google_maps_url = False

    def write(self, vals):
        res = super(IsCentrale, self).write(vals)
        # Si maintenance_date_signature est renseignée, créer une fiche de maintenance
        if 'maintenance_date_signature' in vals and vals['maintenance_date_signature']:
            for record in self:
                # Vérifier qu'il n'existe pas déjà une maintenance pour cette centrale
                existing_maintenance = self.env['is.maintenance'].search([
                    ('centrale_id', '=', record.id),
                ], limit=1)
                if not existing_maintenance:
                    date_signature = fields.Date.from_string(vals['maintenance_date_signature'])
                    date_prevue = date_signature + relativedelta(years=1)
                    self.env['is.maintenance'].create({
                        'centrale_id': record.id,
                        'date_prevue': date_prevue,
                        'technicien_id': self.env.user.id,
                    })
        return res

    @api.model
    def _read_group_dp_etat(self, stages, domain):
        mylist=[]
        for line in self._fields['dp_etat'].selection:
            mylist.append(line[0])
        return mylist

    @api.model
    def _read_group_ptf_etat(self, stages, domain):
        mylist=[]
        for line in self._fields['ptf_etat'].selection:
            mylist.append(line[0])
        return mylist

    @api.model
    def _read_group_crd_etat(self, stages, domain):
        mylist=[]
        for line in self._fields['crd_etat'].selection:
            mylist.append(line[0])
        return mylist

    @api.model
    def _read_group_cardi_etat(self, stages, domain):
        mylist=[]
        for line in self._fields['cardi_etat'].selection:
            mylist.append(line[0])
        return mylist

    @api.model
    def _read_group_socotec_etat(self, stages, domain):
        mylist=[]
        for line in self._fields['socotec_etat'].selection:
            mylist.append(line[0])
        return mylist

    @api.model
    def _read_group_consuel_etat(self, stages, domain):
        mylist=[]
        for line in self._fields['consuel_etat'].selection:
            mylist.append(line[0])
        return mylist


    @api.model
    def _read_group_s21_etat(self, stages, domain):
        mylist=[]
        for line in self._fields['s21_etat'].selection:
            mylist.append(line[0])
        return mylist

    @api.model
    def _read_group_edf_etat(self, stages, domain):
        mylist=[]
        for line in self._fields['edf_etat'].selection:
            mylist.append(line[0])
        return mylist


    def action_view_centrale(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Centrale',
            'res_model': 'is.centrale',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_google_maps_multiple(self):
        """Ouvre une carte OpenStreetMap avec toutes les centrales ayant une localisation"""
        # Récupérer toutes les centrales avec une localisation valide
        centrales_with_location = self.filtered(lambda c: c.localisation)
        
        if not centrales_with_location:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Aucune localisation',
                    'message': 'Aucune centrale sélectionnée ne possède de coordonnées GPS.',
                    'type': 'warning',
                }
            }
        
        # Construire l'URL du contrôleur avec les IDs des centrales
        centrale_ids = ','.join(str(c.id) for c in centrales_with_location)
        url = f'/centrale/map?centrale_ids={centrale_ids}'
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


    # @api.model
    # def _read_group_crd(self, stages, domain):
    #     mylist=[]
    #     for line in self._fields['crd'].selection:
    #         mylist.append(line[0])
    #     return mylist



    # @api.model
    # def _read_group_adm2(self, stages, domain):
    #     mylist=[]
    #     for line in self._fields['adm2'].selection:
    #         mylist.append(line[0])
    #     return mylist

    @api.model
    def _read_group_maintenance_statut(self, stages, domain):
        mylist=[]
        for line in self._fields['maintenance_statut'].selection:
            mylist.append(line[0])
        return mylist

    def action_print_contrat_maintenance(self):
        """Génère le PDF du contrat de maintenance avec les conditions générales"""
        self.ensure_one()
        import base64
        from io import BytesIO
        
        # Générer le PDF du contrat de maintenance
        report = self.env.ref('is_jura_energie_solaire_18.action_report_contrat_maintenance')
        pdf_content, _ = report._render_qweb_pdf(report.id, [self.id])
        
        # Récupérer les conditions générales de la société
        conditions_generales = self.env.company.is_conditions_generales_ids
        
        if not conditions_generales:
            # Pas de conditions générales, retourner directement le PDF du contrat
            return report.report_action(self)
        
        # Assembler les PDFs avec PyPDF2
        try:
            from PyPDF2 import PdfMerger
        except ImportError:
            # Si PyPDF2 n'est pas installé, retourner le PDF sans les conditions
            return report.report_action(self)
        
        merger = PdfMerger()
        
        # Ajouter le PDF du contrat de maintenance
        merger.append(BytesIO(pdf_content))
        
        # Ajouter les PDFs des conditions générales
        for attachment in conditions_generales:
            if attachment.mimetype == 'application/pdf':
                pdf_data = base64.b64decode(attachment.datas)
                merger.append(BytesIO(pdf_data))
        
        # Créer le PDF final
        output = BytesIO()
        merger.write(output)
        merger.close()
        output.seek(0)
        pdf_final = output.read()
        
        # Créer une pièce jointe temporaire pour le téléchargement
        attachment = self.env['ir.attachment'].create({
            'name': f'Contrat_Maintenance_{self.name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_final),
            'mimetype': 'application/pdf',
            'res_model': self._name,
            'res_id': self.id,
        })
        
        # Retourner l'action de téléchargement
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    @api.depends('calendar_event_ids', 'calendar_event_ids.start')
    def _compute_meeting_display(self):
        now = fields.Datetime.now()
        meeting_data = self.env['calendar.event'].sudo()._read_group([
            ('is_centrale_id', 'in', self.ids),
        ], ['is_centrale_id'], ['start:array_agg', 'start:max'])
        mapped_data = {
            centrale: {
                'last_meeting_date': last_meeting_date,
                'next_meeting_date': min([dt for dt in meeting_start_dates if dt > now] or [False]),
            } for centrale, meeting_start_dates, last_meeting_date in meeting_data
        }
        for centrale in self:
            centrale_meeting_info = mapped_data.get(centrale)
            if not centrale_meeting_info:
                centrale.meeting_display_date = False
                centrale.meeting_display_label = 'Pas de réunion'
            elif centrale_meeting_info['next_meeting_date']:
                centrale.meeting_display_date = centrale_meeting_info['next_meeting_date']
                centrale.meeting_display_label = 'Prochaine réunion'
            else:
                centrale.meeting_display_date = centrale_meeting_info['last_meeting_date']
                centrale.meeting_display_label = 'Dernière réunion'

    def action_schedule_meeting(self, smart_calendar=True):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        partner_ids = self.env.user.partner_id.ids
        if self.client_id:
            partner_ids.append(self.client_id.id)
        current_centrale_id = self.id
        action['context'] = {
            'search_default_is_centrale_id': current_centrale_id,
            'default_is_centrale_id': current_centrale_id,
            'default_partner_id': self.client_id.id if self.client_id else False,
            'default_partner_ids': partner_ids,
            'default_name': self.name,
        }
        if smart_calendar:
            mode, initial_date = self._get_centrale_meeting_view_parameters()
            action['context'].update({'default_mode': mode, 'initial_date': initial_date})
        return action

    def _compute_purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = len(rec.purchase_line_ids.mapped('order_id'))

    def action_view_purchase_orders(self):
        self.ensure_one()
        order_ids = self.purchase_line_ids.mapped('order_id').ids
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'name': 'Commandes d\'achat',
            'view_mode': 'list,form',
            'domain': [('id', 'in', order_ids)],
            'context': {'default_is_centrale_id': self.id},
        }

    def action_create_purchase_from_it(self):
        """Crée une commande d'achat avec tous les articles de l'onglet Informations techniques."""
        self.ensure_one()
        PurchaseOrder = self.env['purchase.order']
        partner = self.env.company.partner_id

        order = PurchaseOrder.create({
            'partner_id': partner.id,
            'is_centrale_id': self.id,
            'is_objet': "Matériel - %s" % (self.name or ''),
        })

        lines = []

        # Section Panneaux
        if self.panneau_ids.filtered(lambda l: l.panneau_id and l.quantite):
            lines.append({'order_id': order.id, 'display_type': 'line_section', 'name': 'Panneaux', 'product_qty': 0})

        # Panneaux
        for line in self.panneau_ids:
            if line.panneau_id and line.quantite:
                lines.append({
                    'order_id': order.id,
                    'product_id': line.panneau_id.id,
                    'name': line.panneau_id.display_name,
                    'product_qty': line.quantite,
                    'price_unit': 0,
                    'is_centrale_id': self.id,
                })

        # Section Système d'intégration
        if self.systeme_integration_ids.filtered(lambda l: l.systeme_integration_id and l.quantite):
            lines.append({'order_id': order.id, 'display_type': 'line_section', 'name': "Système d'intégration", 'product_qty': 0})

        # Système d'intégration
        for line in self.systeme_integration_ids:
            if line.systeme_integration_id and line.quantite:
                lines.append({
                    'order_id': order.id,
                    'product_id': line.systeme_integration_id.id,
                    'name': line.systeme_integration_id.display_name,
                    'product_qty': line.quantite,
                    'price_unit': 0,
                    'is_centrale_id': self.id,
                })

        # Section Onduleurs
        if self.onduleur_ids.filtered(lambda l: l.onduleur_id and l.quantite):
            lines.append({'order_id': order.id, 'display_type': 'line_section', 'name': 'Onduleurs', 'product_qty': 0})

        # Onduleurs
        for line in self.onduleur_ids:
            if line.onduleur_id and line.quantite:
                lines.append({
                    'order_id': order.id,
                    'product_id': line.onduleur_id.id,
                    'name': line.onduleur_id.display_name,
                    'product_qty': line.quantite,
                    'price_unit': 0,
                    'is_centrale_id': self.id,
                })

        # Section Optimiseurs
        if self.optimiseur_ids.filtered(lambda l: l.optimiseur_id and l.quantite):
            lines.append({'order_id': order.id, 'display_type': 'line_section', 'name': 'Optimiseurs', 'product_qty': 0})

        # Optimiseurs
        for line in self.optimiseur_ids:
            if line.optimiseur_id and line.quantite:
                lines.append({
                    'order_id': order.id,
                    'product_id': line.optimiseur_id.id,
                    'name': line.optimiseur_id.display_name,
                    'product_qty': line.quantite,
                    'price_unit': 0,
                    'is_centrale_id': self.id,
                })

        # Section Protections électriques
        if self.coffret_ids.filtered(lambda l: l.coffret_id and l.quantite):
            lines.append({'order_id': order.id, 'display_type': 'line_section', 'name': 'Protections électriques', 'product_qty': 0})

        # Protections électriques
        for line in self.coffret_ids:
            if line.coffret_id and line.quantite:
                lines.append({
                    'order_id': order.id,
                    'product_id': line.coffret_id.id,
                    'name': line.coffret_id.display_name,
                    'product_qty': line.quantite,
                    'price_unit': 0,
                    'is_centrale_id': self.id,
                })

        # Section Câbles électriques
        if self.cable_electrique_ids.filtered(lambda l: l.type_cable_id and l.longueur):
            lines.append({'order_id': order.id, 'display_type': 'line_section', 'name': 'Câbles électriques', 'product_qty': 0})

        # Câbles électriques (longueur en mètres comme quantité)
        for line in self.cable_electrique_ids:
            if line.type_cable_id and line.longueur:
                lines.append({
                    'order_id': order.id,
                    'product_id': line.type_cable_id.id,
                    'name': line.type_cable_id.display_name,
                    'product_qty': line.longueur,
                    'price_unit': 0,
                    'is_centrale_id': self.id,
                })

        # Section Autres
        if self.autre_ids.filtered(lambda l: l.produit_id and l.quantite):
            lines.append({'order_id': order.id, 'display_type': 'line_section', 'name': 'Autres', 'product_qty': 0})

        # Autres
        for line in self.autre_ids:
            if line.produit_id and line.quantite:
                lines.append({
                    'order_id': order.id,
                    'product_id': line.produit_id.id,
                    'name': line.produit_id.display_name,
                    'product_qty': line.quantite,
                    'price_unit': 0,
                    'is_centrale_id': self.id,
                })

        if lines:
            self.env['purchase.order.line'].create(lines)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_centrale_meeting_view_parameters(self):
        self.ensure_one()
        meeting_results = self.env["calendar.event"].search_read([('is_centrale_id', '=', self.id)], ['start', 'stop', 'allday'])
        if not meeting_results:
            return "week", False

        user_tz = self.env.user.tz or self.env.context.get('tz')
        user_pytz = pytz.timezone(user_tz) if user_tz else pytz.utc
        meeting_dts = []
        now_dt = datetime.now().astimezone(user_pytz).replace(tzinfo=None)
        for meeting in meeting_results:
            if meeting.get('allday'):
                meeting_dts.append((meeting.get('start'), meeting.get('stop')))
            else:
                meeting_dts.append((
                    meeting.get('start').astimezone(user_pytz).replace(tzinfo=None),
                    meeting.get('stop').astimezone(user_pytz).replace(tzinfo=None),
                ))
        unfinished_meeting_dts = [m for m in meeting_dts if m[1] >= now_dt]
        relevant_meeting_dts = unfinished_meeting_dts if unfinished_meeting_dts else meeting_dts
        if len(relevant_meeting_dts) == 1:
            return "week", relevant_meeting_dts[0][0].date()
        earliest_start_dt = min(m[0] for m in relevant_meeting_dts)
        latest_stop_dt = max(m[1] for m in relevant_meeting_dts)
        lang_week_start = self.env["res.lang"].search_read([('code', '=', self.env.user.lang)], ['week_start'])
        week_start_index = int(lang_week_start[0].get('week_start', '1')) - 1 if lang_week_start else 0
        earliest_start_week_index = earliest_start_dt.weekday() - week_start_index
        latest_stop_week_index = latest_stop_dt.weekday() - week_start_index
        if (latest_stop_dt - earliest_start_dt).days < 7 and earliest_start_week_index <= latest_stop_week_index:
            return "week", earliest_start_dt.date()
        return "month", earliest_start_dt.date()

