# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request


class CentraleMapController(http.Controller):
    
    @http.route('/centrale/map', type='http', auth='user')
    def centrale_map(self, centrale_ids=None, **kwargs):
        """Affiche une carte OpenStreetMap avec les centrales"""
        if not centrale_ids:
            return request.render('is_jura_energie_solaire_18.centrale_map_empty')
        
        # Récupérer les centrales
        try:
            centrale_ids_list = [int(id) for id in centrale_ids.split(',') if id]
            centrales = request.env['is.centrale'].browse(centrale_ids_list)
        except (ValueError, AttributeError):
            return request.render('is_jura_energie_solaire_18.centrale_map_empty')
        
        # Filtrer les centrales avec localisation
        centrales_with_location = centrales.filtered(lambda c: c.localisation)
        
        if not centrales_with_location:
            return request.render('is_jura_energie_solaire_18.centrale_map_empty')
        
        # Préparer les données pour la carte
        markers = []
        for centrale in centrales_with_location:
            try:
                lat, lng = centrale.localisation.split(',')
                markers.append({
                    'lat': float(lat.strip()),
                    'lng': float(lng.strip()),
                    'name': centrale.name,
                    'adresse': centrale.adresse or '',
                    'client': centrale.client_id.name if centrale.client_id else '',
                })
            except (ValueError, AttributeError):
                continue
        
        if not markers:
            return request.render('is_jura_energie_solaire_18.centrale_map_empty')
        
        # Calculer le centre de la carte
        center_lat = sum(m['lat'] for m in markers) / len(markers)
        center_lng = sum(m['lng'] for m in markers) / len(markers)
        
        # Calculer le zoom adapté
        if len(markers) == 1:
            zoom = 15
        else:
            # Calculer l'étendue des coordonnées
            lats = [m['lat'] for m in markers]
            lngs = [m['lng'] for m in markers]
            lat_diff = max(lats) - min(lats)
            lng_diff = max(lngs) - min(lngs)
            max_diff = max(lat_diff, lng_diff)
            
            # Adapter le zoom selon l'étendue
            if max_diff > 5:
                zoom = 7
            elif max_diff > 2:
                zoom = 8
            elif max_diff > 1:
                zoom = 9
            elif max_diff > 0.5:
                zoom = 10
            elif max_diff > 0.1:
                zoom = 11
            else:
                zoom = 12
        
        # Générer le JavaScript complet
        js_code = f"""
            var map = L.map('map').setView([{center_lat}, {center_lng}], {zoom});
            
            // Couche carte normale
            var osmLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19
            }});
            
            // Couche satellite
            var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                attribution: '© Esri',
                maxZoom: 19
            }});
            
            // Ajouter la couche par défaut
            osmLayer.addTo(map);
            
            // Contrôle pour basculer entre les couches
            var baseMaps = {{
                "Carte": osmLayer,
                "Satellite": satelliteLayer
            }};
            L.control.layers(baseMaps).addTo(map);
            
            var markers = {json.dumps(markers)};
            
            markers.forEach(function(marker) {{
                var popupContent = '<div class="popup-title">' + marker.name + '</div>';
                if (marker.client) {{
                    popupContent += '<div class="popup-info"><strong>Client:</strong> ' + marker.client + '</div>';
                }}
                if (marker.adresse) {{
                    popupContent += '<div class="popup-info"><strong>Adresse:</strong> ' + marker.adresse + '</div>';
                }}
                popupContent += '<div class="popup-info"><strong>GPS:</strong> ' + marker.lat + ', ' + marker.lng + '</div>';
                
                L.marker([marker.lat, marker.lng])
                    .addTo(map)
                    .bindPopup(popupContent);
            }});
        """
        
        return request.render('is_jura_energie_solaire_18.centrale_map_view', {
            'markers': markers,
            'js_code': js_code,
        })
