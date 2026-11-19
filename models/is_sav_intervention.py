# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError
from odoo.tools import html_escape
from .is_sav import _ODOO_COLORS


# Champs pouvant être modifiés sur un bon d'intervention validé (changement d'état, facturation et chatter)
_CHAMPS_MODIFIABLES_SI_VALIDE = {'state', 'facturation', 'message_main_attachment_id'}


class IsSavIntervention(models.Model):
    _name = 'is.sav.intervention'
    _description = "Intervention SAV"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'numero'

    numero = fields.Char(string="Numéro", copy=False, readonly=True, default='Nouveau')
    state = fields.Selection(
        [
            ('en_cours', 'En cours'),
            ('valide',   'Validé'),
        ],
        string="Etat",
        default='en_cours',
        required=True,
        copy=False,
        tracking=True,
    )
    sav_id = fields.Many2one('is.sav', string="SAV", required=True, ondelete='cascade', index=True)

    # Informations automatiques reprises du SAV
    centrale_id = fields.Many2one(related='sav_id.centrale_id', string="Centrale", readonly=True)
    secteur = fields.Selection(related='sav_id.secteur', string="Secteur", readonly=True)
    client_id = fields.Many2one(related='sav_id.client_id', string="Client", readonly=True)

    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    intervenant_ids = fields.Many2many(
        'res.users',
        string="Intervenants",
        domain=[('share', '=', False)],
        required=True,
    )
    zone_id = fields.Many2one('is.sav.intervention.zone', string="Zone d'intervention")
    zone_html = fields.Html(compute='_compute_zone_html', string="Zone d'intervention (couleur)", sanitize=False)
    facturation = fields.Selection(
        [
            ('a_facturer',      'À facturer'),
            ('ne_pas_facturer', 'Ne pas facturer'),
            ('a_definir',       'À définir'),
        ],
        string="Facturation",
        default='a_definir',
        required=True,
        tracking=True,
    )
    description = fields.Text(string="Description de l'intervention", required=True)
    fourniture_ids = fields.One2many('is.sav.intervention.fourniture', 'intervention_id', string="Fourniture")
    # Heures et temps de trajet : plus saisis (masqués), conservés pour les anciens bons
    heure_debut = fields.Float(string="Heure de début (trajet inclus)")
    heure_fin = fields.Float(string="Heure de fin (trajet inclus)")
    duree = fields.Float(string="Durée intervention")
    temps_trajet = fields.Float(string="Temps de trajet")

    @api.depends('zone_id', 'zone_id.name', 'zone_id.color')
    def _compute_zone_html(self):
        for rec in self:
            zone = rec.zone_id
            if zone:
                name = html_escape(zone.name or '')
                color = _ODOO_COLORS.get(zone.color, '#FFFFFF')
                rec.zone_html = (
                    f'<span style="background-color: {color}; border: 1px solid rgba(0,0,0,0.15); '
                    f'color: #000; padding: 2px 10px; '
                    f'border-radius: 50rem; white-space: nowrap; font-size: 0.875em;">{name}</span>'
                )
            else:
                rec.zone_html = ''

    @api.constrains('intervenant_ids')
    def _check_intervenant_ids(self):
        for rec in self:
            if not rec.intervenant_ids:
                raise ValidationError("Veuillez indiquer au moins un intervenant.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('numero', 'Nouveau') == 'Nouveau':
                vals['numero'] = self.env['ir.sequence'].next_by_code('is.sav.intervention') or 'Nouveau'
        return super().create(vals_list)

    def write(self, vals):
        if set(vals) - _CHAMPS_MODIFIABLES_SI_VALIDE and any(rec.state == 'valide' for rec in self):
            raise UserError("Un bon d'intervention validé n'est plus modifiable.")
        return super().write(vals)

    def unlink(self):
        if any(rec.state == 'valide' for rec in self):
            raise UserError("Un bon d'intervention validé ne peut pas être supprimé.")
        return super().unlink()

    def action_valider(self):
        a_valider = self.filtered(lambda r: r.state == 'en_cours')
        sans_duree = a_valider.filtered(lambda r: r.duree <= 0.0)
        if sans_duree:
            raise UserError("Veuillez indiquer la durée de l'intervention avant de valider (%s)." % ", ".join(sans_duree.mapped('numero')))
        a_valider.write({'state': 'valide'})

    def action_remettre_en_cours(self):
        self.filtered(lambda r: r.state == 'valide').write({'state': 'en_cours'})

    def action_print_bon_intervention(self):
        self.ensure_one()
        return self.env.ref('is_jura_energie_solaire_18.action_report_bon_intervention').report_action(self)


class IsSavInterventionFourniture(models.Model):
    _name = 'is.sav.intervention.fourniture'
    _description = "Fourniture utilisée lors d'une intervention SAV"
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    intervention_id = fields.Many2one('is.sav.intervention', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Produit")
    reference = fields.Char(string="Référence")
    designation = fields.Char(string="Désignation", required=True)
    quantite = fields.Float(string="Quantité", default=1.0)

    def _check_intervention_modifiable(self):
        if any(rec.intervention_id.state == 'valide' for rec in self):
            raise UserError("Les fournitures d'un bon d'intervention validé ne sont plus modifiables.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_intervention_modifiable()
        return records

    def write(self, vals):
        self._check_intervention_modifiable()
        return super().write(vals)

    def unlink(self):
        self._check_intervention_modifiable()
        return super().unlink()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.reference = self.product_id.default_code
            self.designation = self.product_id.name


class IsSavInterventionZone(models.Model):
    _name = 'is.sav.intervention.zone'
    _description = "Zone d'intervention"
    _order = 'sequence, name'

    sequence = fields.Integer(string="Séquence", default=10)
    name = fields.Char(string="Zone d'intervention", required=True)
    color = fields.Integer(string="Couleur", default=0)
    active = fields.Boolean(string="Actif", default=True)
