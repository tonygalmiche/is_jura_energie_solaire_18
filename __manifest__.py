# -*- coding: utf-8 -*-
{
    "name"     : "Module Odoo 18 pour Jura Energie Solaire",
    "version"  : "0.1",
    "author"   : "InfoSaône",
    "category" : "InfoSaône",
    "description": """
Module Odoo 18 pour Jura Energie Solaire
===================================================
""",
    "maintainer" : "InfoSaône",
    "website"    : "http://www.infosaone.com",
    "depends"    : [
        "base",
        "purchase",
        "product",
        "project",
        "crm",
        "hr_timesheet",
        "l10n_fr_account",
        "web_chatter_position",
    ],
    "data" : [
        "security/is_suivi_temps_security.xml",
        "security/ir.model.access.csv",
        "report/report_contrat_maintenance.xml",
        "views/res_company_view.xml",
        "views/res_partner_view.xml",
        "views/product_view.xml",
        "views/project_view.xml",
        "views/is_sav_view.xml",
        "views/is_centrale_view.xml",
        "views/is_suivi_temps_view.xml",
        "views/calendar_view.xml",
        "views/crm_lead_view.xml",
        "views/menu.xml"
    ],
    'assets': {
        'web.assets_backend': [
            'is_jura_energie_solaire_18/static/src/scss/styles.scss',
            
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
