# -*- coding: utf-8 -*-
from odoo import api, fields, models  

# Liste partagée des secteurs
SECTEUR_SELECTION = [
    ('gp', 'GP'),
    ('re', 'RE'),
    ('th', 'TH'),
    ('si', 'SI'),
]

class IsCentraleAffaire(models.Model):
    _name='is.centrale.affaire'
    _description = "Affaire des centrales"
    _order='name,id'

    name = fields.Char("Affaire")
    centrale_ids = fields.One2many('is.centrale', 'affaire_id', string="Centrales", readonly=True)
    puissance_panneau_totale = fields.Float("Puissance totale (kWc)", compute='_compute_puissance_panneau_totale', store=True)
    euro_par_kwc = fields.Float("€/kWc", compute='_compute_tarifs', store=True, digits=(10, 2))
    forfait = fields.Integer("Forfait", compute='_compute_tarifs', store=True)
    formule_id = fields.Many2one('is.centrale.formule', string="Formule appliquée", compute='_compute_tarifs', store=True)

    @api.depends('puissance_panneau_totale')
    def _compute_tarifs(self):
        for record in self:
            # Recherche de la formule avec la limite la plus proche inférieure
            formule = self.env['is.centrale.formule'].search([
                ('limite_kwc', '<', record.puissance_panneau_totale)
            ], order='limite_kwc desc', limit=1)
            
            # Si non trouvé (puissance < toutes les limites), prendre la plus petite limite
            if not formule:
                formule = self.env['is.centrale.formule'].search([], order='limite_kwc asc', limit=1)
            
            record.euro_par_kwc = formule.euro_par_kwc if formule else 0.0
            record.forfait = formule.forfait if formule else 0
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

    limite_kwc   = fields.Integer("Limite (kWc)", required=True)
    forfait      = fields.Integer("Forfait")
    formule      = fields.Char("Formule")
    euro_par_kwc = fields.Float("€/kWc", compute='_compute_euro_par_kwc', store=True, readonly=True, digits=(10, 2))
    commentaire  = fields.Char("Commentaire")

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
            obj.euro_par_kwc = result
 

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
    quantite           = fields.Integer("Quantité", default=1)
    puissance_onduleur = fields.Integer('Puissance onduleur (kVA)', compute='_compute', store=True, readonly=True)
    puissance_totale   = fields.Integer('Puissance totale (kVA)'  , compute='_compute', store=True, readonly=True)
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
    coffret_id         = fields.Many2one('product.product', string="Coffret")
    quantite           = fields.Integer("Quantité")
 
   
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
    affaire_forfait = fields.Integer(related='affaire_id.forfait', string="Forfait", store=True, tracking=True)
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
    projet_id                = fields.Many2one('project.project', string="Projet")
    localisation             = fields.Char("Localisation", tracking=True)
    adresse                  = fields.Char("Adresse", size=60, tracking=True)
    client_id                = fields.Many2one('res.partner', string="Client", tracking=True)
    client_child_ids = fields.One2many(related="client_id.child_ids")
    sav_ids = fields.One2many('is.sav', 'centrale_id', string="SAVs", tracking=True)
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
    bridage_onduleur = fields.Integer("Bridage onduleur (kVA)", tracking=True)
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

