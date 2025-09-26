# -*- coding: utf-8 -*-
from odoo import fields, models, api  
from datetime import datetime, timedelta
import pytz
from .is_centrale import SECTEUR_SELECTION


class IsSav(models.Model):
    _name='is.sav'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "SAV"
    _order='name'

    name             = fields.Char(string="Nom", size=40, required=True, tracking=True)
    secteur          = fields.Selection(SECTEUR_SELECTION, string="Secteur", tracking=True)
    centrale_id      = fields.Many2one('is.centrale', string="Centrale", tracking=True)
    client_id        = fields.Many2one(related="centrale_id.client_id")
    client_child_ids = fields.One2many(related="centrale_id.client_id.child_ids")
    date_demande     = fields.Date(string="Date demande", tracking=True)
    degre_urgence    = fields.Selection(
        [
            ('non_urgent', 'Non Urgent'),
            ('inter', 'Inter'),
            ('urgent', 'Urgent'),
        ],
        string="Degré d'urgence",
        tracking=True,
        default='non_urgent'
    )
    date_resolution = fields.Date(string="Date de résolution", tracking=True)
    intervenant_ids = fields.Many2many('res.partner', string="Intervenants", tracking=True)
    ticket_number   = fields.Char(string="N°Ticket", size=40, tracking=True)
    description     = fields.Text(string="Description", tracking=True)
    info_depannage  = fields.Text(string="Informations Dépannage", tracking=True)
    state = fields.Selection(
        [
            ('pas_commence', 'Pas commencé'),
            ('en_cours', 'En Cours'),
            ('en_etude', 'En Etude'),
            ('planifie', 'Planifié'),
            ('termine', 'Terminé'),
        ],
        string="Statut",
        tracking=True,
        default='pas_commence',
        group_expand='_read_group_state',
    )

    calendar_event_ids    = fields.One2many('calendar.event', 'is_sav_id', string='Réunion')
    meeting_display_date  = fields.Date(compute="_compute_meeting_display")
    meeting_display_label = fields.Char(compute="_compute_meeting_display")


    @api.depends('calendar_event_ids', 'calendar_event_ids.start')
    def _compute_meeting_display(self):
        now = fields.Datetime.now()
        meeting_data = self.env['calendar.event'].sudo()._read_group([
            ('is_sav_id', 'in', self.ids),
        ], ['is_sav_id'], ['start:array_agg', 'start:max'])
        mapped_data = {
            lead: {
                'last_meeting_date': last_meeting_date,
                'next_meeting_date': min([dt for dt in meeting_start_dates if dt > now] or [False]),
            } for lead, meeting_start_dates, last_meeting_date in meeting_data
        }
        for lead in self:
            lead_meeting_info = mapped_data.get(lead)
            if not lead_meeting_info:
                lead.meeting_display_date = False
                lead.meeting_display_label = 'Pas de réunion'
            elif lead_meeting_info['next_meeting_date']:
                lead.meeting_display_date = lead_meeting_info['next_meeting_date']
                lead.meeting_display_label = 'Prochaine réunion'
            else:
                lead.meeting_display_date = lead_meeting_info['last_meeting_date']
                lead.meeting_display_label = 'Dernière réunion'


    def action_schedule_meeting(self, smart_calendar=True):
        """ Open meeting's calendar view to schedule meeting on current opportunity.

            :param smart_calendar: boolean, to set to False if the view should not try to choose relevant
              mode and initial date for calendar view, see ``_get_opportunity_meeting_view_parameters``
            :return dict: dictionary value for created Meeting view
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        partner_ids = self.env.user.partner_id.ids
        if self.client_id:
            partner_ids.append(self.client_id.id)
        current_sav_id = self.id #if self.type == 'opportunity' else False
        action['context'] = {
            'search_default_is_sav_id': current_sav_id,
            'default_is_sav_id': current_sav_id,
            'default_partner_id': self.client_id.id,
            'default_partner_ids': partner_ids,
            #'default_team_id': self.team_id.id,
            'default_name': self.name,
        }

        # 'Smart' calendar view : get the most relevant time period to display to the user.
        if current_sav_id and smart_calendar:
            mode, initial_date = self._get_opportunity_meeting_view_parameters()
            action['context'].update({'default_mode': mode, 'initial_date': initial_date})

        return action



    def _get_opportunity_meeting_view_parameters(self):
        """ Return the most relevant parameters for calendar view when viewing meetings linked to an opportunity.
            If there are any meetings that are not finished yet, only consider those meetings,
            since the user would prefer no to see past meetings. Otherwise, consider all meetings.
            Allday events datetimes are used without taking tz into account.
            -If there is no event, return week mode and false (The calendar will target 'now' by default)
            -If there is only one, return week mode and date of the start of the event.
            -If there are several events entirely on the same week, return week mode and start of first event.
            -Else, return month mode and the date of the start of first event as initial date. (If they are
            on the same month, this will display that month and therefore show all of them, which is expected)

            :return tuple(mode, initial_date)
                - mode: selected mode of the calendar view, 'week' or 'month'
                - initial_date: date of the start of the first relevant meeting. The calendar will target that date.
        """
        self.ensure_one()
        meeting_results = self.env["calendar.event"].search_read([('is_sav_id', '=', self.id)], ['start', 'stop', 'allday'])
        if not meeting_results:
            return "week", False

        user_tz = self.env.user.tz or self.env.context.get('tz')
        user_pytz = pytz.timezone(user_tz) if user_tz else pytz.utc

        # meeting_dts will contain one tuple of datetimes per meeting : (Start, Stop)
        # meetings_dts and now_dt are as per user time zone.
        meeting_dts = []
        now_dt = datetime.now().astimezone(user_pytz).replace(tzinfo=None)

        # When creating an allday meeting, whatever the TZ, it will be stored the same e.g. 00.00.00->23.59.59 in utc or
        # 08.00.00->18.00.00. Therefore we must not put it back in the user tz but take it raw.
        for meeting in meeting_results:
            if meeting.get('allday'):
                meeting_dts.append((meeting.get('start'), meeting.get('stop')))
            else:
                meeting_dts.append((meeting.get('start').astimezone(user_pytz).replace(tzinfo=None),
                                   meeting.get('stop').astimezone(user_pytz).replace(tzinfo=None)))

        # If there are meetings that are still ongoing or to come, only take those.
        unfinished_meeting_dts = [meeting_dt for meeting_dt in meeting_dts if meeting_dt[1] >= now_dt]
        relevant_meeting_dts = unfinished_meeting_dts if unfinished_meeting_dts else meeting_dts
        relevant_meeting_count = len(relevant_meeting_dts)

        if relevant_meeting_count == 1:
            return "week", relevant_meeting_dts[0][0].date()
        else:
            # Range of meetings
            earliest_start_dt = min(relevant_meeting_dt[0] for relevant_meeting_dt in relevant_meeting_dts)
            latest_stop_dt = max(relevant_meeting_dt[1] for relevant_meeting_dt in relevant_meeting_dts)

            # The week start day depends on language. We fetch the week_start of user's language. 1 is monday.
            lang_week_start = self.env["res.lang"].search_read([('code', '=', self.env.user.lang)], ['week_start'])
            # We substract one to make week_start_index range 0-6 instead of 1-7
            week_start_index = int(lang_week_start[0].get('week_start', '1')) - 1

            # We compute the weekday of earliest_start_dt according to week_start_index. earliest_start_dt_index will be 0 if we are on the
            # first day of the week and 6 on the last. weekday() returns 0 for monday and 6 for sunday. For instance, Tuesday in UK is the
            # third day of the week, so earliest_start_dt_index is 2, and remaining_days_in_week includes tuesday, so it will be 5.
            # The first term 7 is there to avoid negative left side on the modulo, improving readability.
            earliest_start_dt_weekday = (7 + earliest_start_dt.weekday() - week_start_index) % 7
            remaining_days_in_week = 7 - earliest_start_dt_weekday

            # We compute the start of the week following the one containing the start of the first meeting.
            next_week_start_date = earliest_start_dt.date() + timedelta(days=remaining_days_in_week)

            # Latest_stop_dt must be before the start of following week. Limit is therefore set at midnight of first day, included.
            meetings_in_same_week = latest_stop_dt <= datetime(next_week_start_date.year, next_week_start_date.month, next_week_start_date.day, 0, 0, 0)

            if meetings_in_same_week:
                return "week", earliest_start_dt.date()
            else:
                return "month", earliest_start_dt.date()


    @api.onchange('centrale_id')
    def _onchange_centrale_id(self):
        """Récupère le secteur de la centrale sélectionnée"""
        if self.centrale_id and self.centrale_id.secteur:
            self.secteur = self.centrale_id.secteur

    @api.model
    def _read_group_state(self, stages, domain):
        mylist=[]
        for line in self._fields['state'].selection:
            mylist.append(line[0])
        return mylist
    
