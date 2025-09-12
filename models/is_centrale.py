# -*- coding: utf-8 -*-
from odoo import api, fields, models  



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

    centrale_id        = fields.Many2one('is.centrale', 'Centrale', required=True, ondelete='cascade')
    sequence           = fields.Integer("Ordre")
    onduleur_id        = fields.Many2one('product.product', string="Onduleur")
    quantite           = fields.Integer("Quantité")
    puissance_onduleur = fields.Integer('Puissance onduleur (kVA)', compute='_compute', store=True, readonly=True)
    puissance_totale   = fields.Integer('Puissance totale (kVA)'  , compute='_compute', store=True, readonly=True)
 
    @api.depends('onduleur_id','onduleur_id.product_tmpl_id.is_puissance_kva','quantite','puissance_onduleur')
    def _compute(self):
        for obj in self:
            puissance_onduleur = 0
            if obj.onduleur_id:
                puissance_onduleur = obj.onduleur_id.product_tmpl_id.is_puissance_kva
            obj.puissance_onduleur = puissance_onduleur
            obj.puissance_totale  = puissance_onduleur * obj.quantite 




class IsCentraleCoffret(models.Model):
    _name='is.centrale.coffret'
    _description = "Coffrets des centrales"
    _order='sequence,id'

    centrale_id        = fields.Many2one('is.centrale', 'Centrale', required=True, ondelete='cascade')
    sequence           = fields.Integer("Ordre")
    coffret_id         = fields.Many2one('product.product', string="Coffret")
    quantite           = fields.Integer("Quantité")
 
   
class IsCentrale(models.Model):
    _name='is.centrale'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Centrale"
    _order='name'

    name                     = fields.Char("Nom", size=40, required=True, tracking=True)
    secteur = fields.Selection(
        [
            ('gp', 'GP'),
            ('re', 'RE'),
            ('th', 'TH'),
            ('si', 'SI'),
        ],
        string="Secteur",
        tracking=True,
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
    projet_id                = fields.Many2one('project.project', string="Projet")
    localisation             = fields.Char("Localisation", tracking=True)
    adresse                  = fields.Char("Adresse", size=60, tracking=True)
    client_id                = fields.Many2one('res.partner', string="Client", tracking=True)
    client_child_ids = fields.One2many(related="client_id.child_ids")
    sav_ids = fields.One2many('is.sav', 'centrale_id', string="SAVs", tracking=True)
    puissance_onduleur_demandee = fields.Integer(string="Puissance onduleurs demandée (kVA)")
    puissance_panneau_demandee  = fields.Integer(string="Puissance panneaux demandée (kWc)")
    puissance_onduleur_totale = fields.Integer(
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
    crd_recu         = fields.Date("CRD Reçu", tracking=True)
    crd_signature    = fields.Date("CRD Signature", tracking=True)
    crd_informations = fields.Text("CRD Informations", tracking=True)

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
    coffret_ids  = fields.One2many('is.centrale.coffret' , 'centrale_id', 'Coffrets')
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


    @api.onchange('crd_etat')
    def onchange_crd_etat(self):
        for obj in self:
            print(obj,obj.crd_etat)
            if obj.crd_etat=='signe':
                obj.cardi_etat='a_faire'


    @api.depends('onduleur_ids.puissance_totale')
    def _compute_puissance_onduleur_totale(self):
        for record in self:
            record.puissance_onduleur_totale = sum(
                onduleur.puissance_totale for onduleur in record.onduleur_ids
            )

    @api.depends('panneau_ids.puissance_totale')
    def _compute_puissance_panneau_totale(self):
        for record in self:
            record.puissance_panneau_totale = sum(
                panneau.puissance_totale for panneau in record.panneau_ids
            )

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

