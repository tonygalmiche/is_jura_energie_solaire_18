# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError
from markupsafe import Markup


# Champs pouvant être modifiés sur un bon d'intervention validé (changement d'état et chatter)
_CHAMPS_MODIFIABLES_SI_VALIDE = {'state', 'message_main_attachment_id'}


def _format_heure(heures):
    """8.5 -> '8h30'"""
    minutes = int(round(heures * 60))
    return "%dh%02d" % (minutes // 60, minutes % 60)


def _lien(record):
    """Lien cliquable vers un enregistrement, pour le chatter"""
    return Markup('<a href="#" data-oe-model="%s" data-oe-id="%s">%s</a>') % (
        record._name, record.id, record.display_name)


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
    description = fields.Text(string="Description de l'intervention", required=True)
    fourniture_ids = fields.One2many('is.sav.intervention.fourniture', 'intervention_id', string="Fourniture")
    heure_debut = fields.Float(string="Heure de début (trajet inclus)")
    heure_fin = fields.Float(string="Heure de fin (trajet inclus)")
    duree = fields.Float(string="Durée intervention", compute='_compute_duree', store=True)
    temps_trajet = fields.Float(string="Temps de trajet")

    @api.depends('heure_debut', 'heure_fin', 'temps_trajet')
    def _compute_duree(self):
        for rec in self:
            rec.duree = max(rec.heure_fin - rec.heure_debut - (rec.temps_trajet or 0.0), 0.0)

    @api.constrains('intervenant_ids')
    def _check_intervenant_ids(self):
        for rec in self:
            if not rec.intervenant_ids:
                raise ValidationError("Veuillez indiquer au moins un intervenant.")

    @api.constrains('heure_debut', 'heure_fin', 'temps_trajet')
    def _check_heures(self):
        for rec in self:
            if not rec.heure_debut and not rec.heure_fin:
                continue
            if rec.heure_fin <= rec.heure_debut:
                raise ValidationError("L'heure de fin doit être supérieure à l'heure de début.")
            if rec.heure_fin - rec.heure_debut - (rec.temps_trajet or 0.0) <= 0.0:
                raise ValidationError("La durée de l'intervention (après déduction du temps de trajet) doit être supérieure à 0.")

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
        for rec in self.filtered(lambda r: r.state == 'en_cours'):
            rec._ajouter_suivi_temps()
            rec.write({'state': 'valide'})

    def action_remettre_en_cours(self):
        for rec in self.filtered(lambda r: r.state == 'valide'):
            rec._supprimer_suivi_temps()
            rec.write({'state': 'en_cours'})

    def _get_commentaire_suivi_temps(self):
        return "SAV %s - Bon d'intervention %s" % (self.sav_id.name, self.numero)

    def _ajouter_suivi_temps(self):
        """Ajoute le temps du bon dans la saisie journalière de chaque intervenant :
        création de la saisie si elle n'existe pas, sinon ajout d'une ligne SAV
        et allongement de la journée de la durée du bon"""
        self.ensure_one()
        if not self.heure_debut or not self.heure_fin:
            raise UserError("Les heures de début et de fin sont obligatoires pour valider le bon d'intervention.")
        Saisie = self.env['is.suivi.temps.saisie'].sudo()
        duree = self.heure_fin - self.heure_debut
        commentaire = self._get_commentaire_suivi_temps()
        vals_ligne = {
            'type_travail': 'sav',
            'centrale_id': self.centrale_id.id,
            'duree': duree,
            'sav_intervention_id': self.id,
        }
        messages = []
        for user in self.intervenant_ids:
            saisie = Saisie.search([('utilisateur_id', '=', user.id), ('date', '=', self.date)], limit=1)
            try:
                if not saisie:
                    saisie = Saisie.create({
                        'utilisateur_id': user.id,
                        'date': self.date,
                        'heure_debut': self.heure_debut,
                        'heure_fin': self.heure_fin,
                        'temps_pose': 0.0,
                        'heure_route': self.temps_trajet,
                        'commentaire': commentaire,
                        'ligne_ids': [(0, 0, vals_ligne)],
                    })
                    messages.append(Markup("%s : saisie créée (%s de SAV) %s") % (
                        user.name, _format_heure(duree), _lien(saisie)))
                    continue
                heure_fin = saisie.heure_fin + duree
                if heure_fin > 24:
                    raise ValidationError("L'ajout de %.2fh ferait dépasser minuit (heure de fin de la saisie)." % duree)
                sequence = max(saisie.ligne_ids.mapped('sequence') or [0]) + 10
                saisie.write({
                    'heure_fin': heure_fin,
                    'heure_route': (saisie.heure_route or 0.0) + (self.temps_trajet or 0.0),
                    'commentaire': "\n".join(filter(None, [saisie.commentaire, commentaire])),
                    'ligne_ids': [(0, 0, dict(vals_ligne, sequence=sequence))],
                })
                messages.append(Markup("%s : saisie mise à jour (ajout de %s de SAV, fin de journée à %s) %s") % (
                    user.name, _format_heure(duree), _format_heure(heure_fin), _lien(saisie)))
            except ValidationError as e:
                raise ValidationError(
                    "Impossible de mettre à jour le suivi du temps de %s le %s :\n%s"
                    % (user.name, self.date.strftime('%d/%m/%Y'), e.args[0])
                )
        self._poster_message_suivi_temps("Suivi du temps mis à jour", messages)

    def _poster_message_suivi_temps(self, titre, messages):
        if messages:
            self.message_post(body=Markup("<p><b>%s le %s :</b></p><ul>%s</ul>") % (
                titre,
                self.date.strftime('%d/%m/%Y'),
                Markup("").join(Markup("<li>%s</li>") % m for m in messages),
            ))

    def _supprimer_suivi_temps(self):
        """Retire le temps du bon des saisies journalières : suppression de la ligne SAV
        (et de la saisie si elle ne contenait que cette ligne), sinon réduction de la journée"""
        self.ensure_one()
        lignes = self.env['is.suivi.temps.saisie.ligne'].sudo().search([('sav_intervention_id', '=', self.id)])
        commentaire = self._get_commentaire_suivi_temps()
        messages = []
        for ligne in lignes:
            saisie = ligne.saisie_id
            user_name = saisie.utilisateur_id.name
            if saisie.ligne_ids == ligne:
                saisie.unlink()
                messages.append(Markup("%s : saisie supprimée (elle ne contenait que ce bon)") % user_name)
                continue
            lignes_commentaire = (saisie.commentaire or '').split("\n")
            if commentaire in lignes_commentaire:
                lignes_commentaire.remove(commentaire)
            duree = ligne.duree
            heure_fin = saisie.heure_fin - duree
            saisie.write({
                'heure_fin': heure_fin,
                'heure_route': max((saisie.heure_route or 0.0) - (self.temps_trajet or 0.0), 0.0),
                'commentaire': "\n".join(lignes_commentaire) or False,
                'ligne_ids': [(2, ligne.id)],
            })
            messages.append(Markup("%s : saisie mise à jour (retrait de %s de SAV, fin de journée à %s) %s") % (
                user_name, _format_heure(duree), _format_heure(heure_fin), _lien(saisie)))
        self._poster_message_suivi_temps("Suivi du temps retiré", messages)

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
