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
    
    is_provenance_client_id = fields.Many2one('is.provenance.client', string="Provenance client", tracking=True)
    is_secteur      = fields.Selection(SECTEUR_SELECTION,string="Secteur",tracking=True)
    is_adresse      = fields.Char("Adresse", size=60, tracking=True, required=False)
    is_localisation = fields.Char("Localisation", tracking=True)
    is_centrale_id  = fields.Many2one('is.centrale', string="Centrale", tracking=True)
    is_date_changement_etat = fields.Datetime("Date de dernier changement d'état", readonly=True, tracking=True)

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
