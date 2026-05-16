# -*- coding: utf-8 -*-
from odoo import fields, models, api  
from markupsafe import Markup
from .is_centrale import SECTEUR_SELECTION


class IsProvenanceClient(models.Model):
    _name = 'is.provenance.client'
    _description = "Provenance client"
    _order = 'name'

    name = fields.Char("Nom", required=True)


class crm_lead(models.Model):
    _inherit = "crm.lead"
    _order = 'sequence, priority desc, id desc'

    # Le champ doit s'appeler exactement "sequence" (DEFAULT_HANDLE_FIELD dans le JS Odoo 18)
    # pour que le drag-and-drop vertical dans les colonnes kanban soit activé automatiquement.
    sequence        = fields.Integer('Ordre', default=10)
    is_provenance_client_id = fields.Many2one('is.provenance.client', string="Provenance client", tracking=True)
    is_secteur      = fields.Selection(SECTEUR_SELECTION,string="Secteur",tracking=True)
    is_sous_secteur = fields.Selection([('chantier', 'Chantier'), ('sav', 'SAV')], string="Sous secteur", default='chantier', tracking=True)
    is_adresse      = fields.Char("Adresse", size=60, tracking=True, required=False)
    is_localisation = fields.Char("Localisation", tracking=True)
    is_centrale_id  = fields.Many2one('is.centrale', string="Centrale", tracking=True)
    is_date_changement_etat = fields.Datetime("Date de dernier changement d'état", readonly=False, tracking=True)
    is_date_premiere_reunion  = fields.Date("Date de première réunion", readonly=True, tracking=True)
    is_delai_prise_en_compte  = fields.Integer("Délai de prise en compte de la demande (jours)", readonly=True, tracking=True)
    is_devis_signe_ids = fields.Many2many(
        'ir.attachment',
        'crm_lead_devis_signe_rel',
        'lead_id',
        'attachment_id',
        string="Devis signé",
    )
    is_memoire_technique_ids = fields.Many2many(
        'ir.attachment',
        'crm_lead_memoire_technique_rel',
        'lead_id',
        'attachment_id',
        string="Mémoire technique",
    )
    is_etude_ids = fields.Many2many(
        'ir.attachment',
        'crm_lead_etude_rel',
        'lead_id',
        'attachment_id',
        string="Etude",
    )

    def write(self, vals):
        # Mettre à jour la date de changement d'état si stage_id est modifié
        if 'stage_id' in vals:
            vals['is_date_changement_etat'] = fields.Datetime.now()
        return super(crm_lead, self).write(vals)

    def action_create_centrale(self):
        self.ensure_one()
        if not self.partner_id:
            raise models.UserError("Vous devez renseigner le contact (client) avant de créer une centrale.")
        centrale = self.env['is.centrale'].create({
            'name': self.name,
            'client_id': self.partner_id.id,
            'localisation': self.is_localisation,
            'secteur': self.is_secteur,
            'adresse': self.is_adresse,
        })
        self.is_centrale_id = centrale.id
        
        # Message dans le chatter de l'opportunité
        self.message_post(
            body=Markup(f"""
                <p>Centrale créée : <a href="#" data-oe-model="is.centrale" data-oe-id="{centrale.id}">{centrale.name}</a></p>
                <ul>
                    <li>Client : {self.partner_id.name}</li>
                    <li>Secteur : {dict(self._fields['is_secteur'].selection).get(self.is_secteur, '')}</li>
                    <li>Localisation : {self.is_localisation or ''}</li>
                    <li>Adresse : {self.is_adresse or ''}</li>
                </ul>
            """)
        )
        
        # Message dans le chatter de la centrale
        centrale.message_post(
            body=Markup(f"""
                <p>Centrale créée depuis l'opportunité : <a href="#" data-oe-model="crm.lead" data-oe-id="{self.id}">{self.name}</a></p>
                <ul>
                    <li>Client : {self.partner_id.name}</li>
                    <li>Secteur : {dict(self._fields['is_secteur'].selection).get(self.is_secteur, '')}</li>
                    <li>Localisation : {self.is_localisation or ''}</li>
                    <li>Adresse : {self.is_adresse or ''}</li>
                </ul>
            """)
        )
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'is.centrale',
            'res_id': centrale.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_open_lead(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_recalcul_premiere_reunion(self):
        """Action serveur : recalcule la date de première réunion et le délai pour les leads sélectionnés."""
        for lead in self:
            first_meeting = self.env['calendar.event'].search(
                [('opportunity_id', '=', lead.id)],
                order='start asc',
                limit=1,
            )
            if first_meeting:
                start_date = first_meeting.start.date()
                delta = (start_date - lead.create_date.date()).days
                lead.write({
                    'is_date_premiere_reunion': start_date,
                    'is_delai_prise_en_compte': delta,
                })
            else:
                lead.write({
                    'is_date_premiere_reunion': False,
                    'is_delai_prise_en_compte': 0,
                })
