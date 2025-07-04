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
    das = fields.Selection(
        [
            ('gp_agri', 'GP - Agri'),
            ('gp_ci', 'GP - C&I'),
            ('gp_collectivite', 'GP - Collectivité'),
            ('re', 'RE'),
            ('th', 'TH'),
            ('si', 'SI'),
        ],
        string="DAS",
        tracking=True,
    )

    projet_id                = fields.Many2one('project.project', string="Projet")

 
    localisation             = fields.Char("Localisation", tracking=True)
    adresse                  = fields.Char("Adresse", size=60, tracking=True)
    client_id                = fields.Many2one('res.partner', string="Client", tracking=True, domain=[("is_company","=",True)])
    client_child_ids = fields.One2many(related="client_id.child_ids")
    adm1 = fields.Selection(
        [
            ('dp_a_faire', 'DP à faire'),
            ('dp_envoye_client', 'DP envoyé Client'),
            ('dp_depose_mairie', 'DP déposé Mairie'),
            ('ptf_a_faire', 'PTF à faire'),
            ('ptf_depose', 'PTF déposé'),
            ('ptf_completude', 'PTF complétude'),
            ('ptf_obtenu', 'PTF obtenu'),
        ],
        string="ADM 1",
        tracking=True,
        group_expand='_read_group_adm1',
    )
    date_depose_dp           = fields.Date("Date Dépose DP", tracking=True)
    reference_enedis         = fields.Char("Référence Enedis", size=20, tracking=True)
    ptf_depose               = fields.Date("PTF Déposé", tracking=True)
    ptf_obtenu               = fields.Date("PTF Obtenu", tracking=True)
    dp_ptf_informations      = fields.Text("DP/PTF Informations", tracking=True)
    crd = fields.Selection(
        [
            ('recu', 'Reçu'),
            ('a_traiter', 'A traiter'),
            ('chez_client', 'Chez le client'),
            ('signe', 'Signé'),
        ],
        string="CRD",
        tracking=True,
        group_expand='_read_group_crd',
    )

    crd_recu                 = fields.Date("CRD reçu", tracking=True)
    adm2 = fields.Selection(
        [
            ('en_attente', 'En attente'),
            ('crd_recu', 'CRD Reçu'),
            ('crd_signe', 'CRD Signé'),
            ('cardi_a_faire', 'CARD-I à Faire'),
            ('cardi_client', 'CARD-I Client'),
            ('cardi_enedis', 'CARD-I Enedis'),
            ('obtenu', 'Obtenu'),
        ],
        string="ADM 2",
        tracking=True,
        group_expand='_read_group_adm2',
    )

    cardi_depose             = fields.Date("CARD-I Déposé", tracking=True)
    crd_cardi_informations   = fields.Text("CRD/CARD-I Informations", tracking=True)
    socotec = fields.Selection(
        [
            ('a_planifier', 'A Planifier'),
            ('planifie', 'Planifié'),
        ],
        string="Socotec",
        tracking=True,
    )
    socotec_date             = fields.Date("Socotec Date", tracking=True)
    consuel = fields.Selection(
        [
            ('a_faire', 'A Faire'),
            ('depose', 'Déposé'),
            ('obtenu', 'Obtenu'),
        ],
        string="Consuel",
        tracking=True,
    )
    consuel_depose           = fields.Date("Consuel Dépose", tracking=True)
    mes_date                 = fields.Date("MES Date", tracking=True)
    info_mise_en_service     = fields.Text("Informations Mise en Service", tracking=True)

    sav_ids = fields.One2many('is.sav', 'centrale_id', string="SAVs", tracking=True)

    panneau_ids  = fields.One2many('is.centrale.panneau' , 'centrale_id', 'Panneaux')
    onduleur_ids = fields.One2many('is.centrale.onduleur', 'centrale_id', 'Onduleurs')
    coffret_ids  = fields.One2many('is.centrale.coffret' , 'centrale_id', 'Coffrets')
    puissance_onduleur_totale = fields.Integer(
        string="Puissance des onduleurs (kVA)",
        compute="_compute_puissance_onduleur_totale",
        store=True,
        readonly=True,
    )
    puissance_panneau_totale = fields.Float(
        string="Puissance des panneaux (kW)",
        compute="_compute_puissance_panneau_totale",
        store=True,
        readonly=True,
        digits=(3, 2),
    )

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
    def _read_group_adm1(self, stages, domain):
        mylist=[]
        for line in self._fields['adm1'].selection:
            mylist.append(line[0])
        return mylist


    @api.model
    def _read_group_crd(self, stages, domain):
        mylist=[]
        for line in self._fields['crd'].selection:
            mylist.append(line[0])
        return mylist



    @api.model
    def _read_group_adm2(self, stages, domain):
        mylist=[]
        for line in self._fields['adm2'].selection:
            mylist.append(line[0])
        return mylist

