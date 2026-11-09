# -*- coding: utf-8 -*-
# Intervenants des SAV : passage des contacts (res.partner) aux utilisateurs (res.users)
# Ancienne table : is_sav_res_partner_rel (conservée), nouvelle : is_sav_res_users_rel
import logging

_logger = logging.getLogger(__name__)

# Contacts sans lien avec un utilisateur : nom du contact -> login de l'utilisateur
CORRESPONDANCES = {
    "David Putigny"    : "davidjuraenergiesolaire@gmail.com",
    "DEBORD Nicolas"   : "nicolas.debord@jura-energiesolaire.com",
    "ETIEVANT Natahlie": "info@jura-energiesolaire.com",
    "VAN ROSSUM Lucas" : "lvr@jura-energiesolaire.com",
    "SCHILLIGER Marc"  : "marcjes06@gmail.com",
    "Matthew PERRETTO" : "matthew.perretto.jes@gmail.com",
    "SALVADORI Michel" : "michel.salvadori@jura-energiesolaire.com",
    # Contacts présents seulement sur des bases plus anciennes (test)
    "Benoit Grangeot (ne pas utiliser)": "benoitjes05@gmail.com",
    "DUMONT  Guillaume": "guillaume.dumont@jura-energiesolaire.com",  # deux espaces
    "Nathan Gaillard"  : "nathangaillard.jes@gmail.com",
}


def migrate(cr, version):
    cr.execute("SELECT to_regclass('is_sav_res_partner_rel')")
    if not cr.fetchone()[0]:
        _logger.info("Intervenants SAV : pas d'ancienne table is_sav_res_partner_rel, rien à reprendre")
        return

    cr.execute("""
        SELECT DISTINCT p.id, p.name
        FROM is_sav_res_partner_rel r
        JOIN res_partner p ON p.id = r.res_partner_id
    """)
    partenaires = cr.fetchall()

    nb = 0
    for partner_id, nom in partenaires:
        # 1) Contact d'un utilisateur
        cr.execute("SELECT id FROM res_users WHERE partner_id = %s ORDER BY active DESC, id LIMIT 1", (partner_id,))
        row = cr.fetchone()
        # 2) Correspondance par le nom
        if not row and nom in CORRESPONDANCES:
            cr.execute("SELECT id FROM res_users WHERE login = %s", (CORRESPONDANCES[nom],))
            row = cr.fetchone()
        if not row:
            cr.execute("SELECT is_sav_id FROM is_sav_res_partner_rel WHERE res_partner_id = %s", (partner_id,))
            sav_ids = [r[0] for r in cr.fetchall()]
            _logger.warning("Intervenants SAV : aucun utilisateur pour le contact %s (id %s), SAV %s non repris",
                            nom, partner_id, sav_ids)
            continue
        cr.execute("""
            INSERT INTO is_sav_res_users_rel (is_sav_id, res_users_id)
            SELECT is_sav_id, %s FROM is_sav_res_partner_rel WHERE res_partner_id = %s
            ON CONFLICT DO NOTHING
        """, (row[0], partner_id))
        nb += cr.rowcount
    _logger.info("Intervenants SAV : %s liens SAV / utilisateur créés", nb)
