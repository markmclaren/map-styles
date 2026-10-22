#!/usr/bin/env python3
"""
compile_styles.py
Compiles open-source vector basemap color schemes into MapLibre styles powered by OpenFreeMap.
Renders cartographic themes onto the OpenMapTiles schema.
Outputs 13 style variants into dist/.
"""

import os
import json
import copy

SPRITE_URL = "https://tiles.openfreemap.org/sprites/ofm_f384/ofm"
GLYPHS_URL = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf"
TILE_SOURCE_URL = "https://tiles.openfreemap.org/planet"
SHADED_RELIEF_URL = "https://tiles.openfreemap.org/natural_earth/ne2sr/{z}/{x}/{y}.png"

FONT_MAP = {
    'bold': ['Noto Sans Bold'],
    'regular': ['Noto Sans Regular'],
    'italic': ['Noto Sans Italic']
}

def clean_fonts(layer):
    """Ensure fontstack uses OpenFreeMap Noto Sans fonts."""
    if layer.get('type') == 'symbol':
        layout = layer.get('layout', {})
        text_font = layout.get('text-font')
        if text_font:
            if any('bold' in f.lower() for f in text_font):
                layout['text-font'] = FONT_MAP['bold']
            elif any('italic' in f.lower() or 'oblique' in f.lower() for f in text_font):
                layout['text-font'] = FONT_MAP['italic']
            else:
                layout['text-font'] = FONT_MAP['regular']

def get_glacier_color(theme_config):
    """
    Returns an appropriate glacier/ice color for the theme.
    Respects theme_config['glacier_fill'] if set.
    For dark themes without an explicit glacier_fill, derives a harmonious dark ice shade
    rather than pure white.
    """
    if 'glacier_fill' in theme_config:
        return theme_config['glacier_fill']

    base = theme_config.get('land_fill', theme_config.get('background', '#ffffff'))
    if isinstance(base, dict) and 'stops' in base:
        base = base['stops'][0][1]

    if isinstance(base, str) and base.startswith('#'):
        try:
            h = base.lstrip('#')
            if len(h) == 3:
                h = ''.join(c * 2 for c in h)
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0

            # If dark theme (luminance < 0.4), lighten slightly for subtle cool ice distinction
            if lum < 0.4:
                nr = min(255, int(r * 1.35 + 14))
                ng = min(255, int(g * 1.35 + 18))
                nb = min(255, int(b * 1.4 + 28))
                return f"#{nr:02x}{ng:02x}{nb:02x}"
        except Exception:
            pass

    return '#ffffff'

def compile_style(base_template, theme_config, is_base_only=False, is_ref_only=False, include_relief=False):
    """
    Transforms an OpenMapTiles template JSON using theme_config rules.
    """
    style = copy.deepcopy(base_template)
    style['name'] = theme_config['name']
    style['sprite'] = SPRITE_URL
    style['glyphs'] = GLYPHS_URL

    # Configure sources
    style['sources'] = {
        'openmaptiles': {
            'type': 'vector',
            'url': TILE_SOURCE_URL
        }
    }

    if include_relief:
        style['sources']['ne2_shaded'] = {
            'type': 'raster',
            'tileSize': 256,
            'maxzoom': 6,
            'tiles': [SHADED_RELIEF_URL]
        }

    new_layers = []

    for layer in style.get('layers', []):
        l_id = layer.get('id', '')
        l_type = layer.get('type', '')
        s_layer = layer.get('source-layer', '')

        # Filter base vs reference
        is_label = (l_type == 'symbol') or ('label' in l_id.lower()) or (s_layer in ['place', 'poi', 'water_name', 'transportation_name', 'housenumber', 'aerodrome_label'])
        
        if is_base_only and is_label:
            continue
        if is_ref_only and not is_label and l_id != 'boundary_country' and 'boundary' not in l_id:
            continue

        clean_fonts(layer)

        paint = layer.setdefault('paint', {})
        layout = layer.setdefault('layout', {})

        # Apply Background
        if l_type == 'background':
            if is_ref_only:
                paint['background-opacity'] = 0
            else:
                paint['background-color'] = theme_config.get('background', '#ffffff')
            new_layers.append(layer)

            # Insert relief underlay immediately after background
            if include_relief and not is_ref_only:
                new_layers.append({
                    "id": "natural_earth_relief",
                    "type": "raster",
                    "source": "ne2_shaded",
                    "maxzoom": 7,
                    "paint": {
                        "raster-opacity": [
                            "interpolate",
                            ["exponential", 1.5],
                            ["zoom"],
                            0, 0.55,
                            6, 0.15
                        ]
                    }
                })
            continue

        # Apply Waterways (Rivers, Streams, Canals)
        elif (s_layer == 'waterway' or 'waterway' in l_id or 'river' in l_id) and l_type == 'line':
            paint['line-color'] = theme_config.get('waterway_line', theme_config.get('water_fill', '#a7d6fe'))

        # Apply Water Bodies (Lakes, Oceans, Reservoirs)
        elif (s_layer == 'water' or l_id == 'water' or l_id.startswith('water-') or (l_type == 'fill' and 'water' in l_id and 'waterway' not in l_id)) and l_type == 'fill':
            paint['fill-color'] = theme_config.get('water_fill', '#a7d6fe')
            if 'water_outline' in theme_config:
                paint['fill-outline-color'] = theme_config['water_outline']
            new_layers.append(layer)
            if l_id == 'water' and 'water_outline' in theme_config and not is_ref_only:
                new_layers.append({
                    "id": "water_coastline_edge",
                    "type": "line",
                    "source": "openmaptiles",
                    "source-layer": "water",
                    "paint": {
                        "line-color": theme_config['water_outline'],
                        "line-width": [
                            "interpolate",
                            ["exponential", 1.2],
                            ["zoom"],
                            0, 1.0,
                            6, 1.4,
                            12, 2.0
                        ]
                    }
                })
            continue

        # Apply Landcover / Landuse
        elif s_layer in ['landcover', 'landuse', 'park']:
            if l_type == 'fill':
                if any(w in l_id for w in ['wood', 'forest']):
                    paint['fill-color'] = theme_config.get('wood_fill', '#bdf2af')
                elif any(w in l_id for w in ['park', 'grass', 'garden']):
                    paint['fill-color'] = theme_config.get('park_fill', '#ccebb5')
                elif any(w in l_id for w in ['residential', 'suburb']):
                    paint['fill-color'] = theme_config.get('residential_fill', theme_config.get('land_fill', '#f4f4f4'))
                elif any(w in l_id for w in ['commercial', 'retail']):
                    paint['fill-color'] = theme_config.get('commercial_fill', theme_config.get('residential_fill', '#f4f4f4'))
                elif any(w in l_id for w in ['industrial', 'railway']):
                    paint['fill-color'] = theme_config.get('industrial_fill', '#e5e5e5')
                elif any(w in l_id for w in ['cemetery', 'hospital', 'school']):
                    paint['fill-color'] = theme_config.get('special_fill', theme_config.get('park_fill', '#ccebb5'))
                elif 'sand' in l_id or 'beach' in l_id:
                    paint['fill-color'] = theme_config.get('sand_fill', '#f5edd6')
                elif any(w in l_id for w in ['glacier', 'ice']) and 'service' not in l_id:
                    paint['fill-color'] = get_glacier_color(theme_config)
                    if 'glacier_opacity' in theme_config:
                        paint['fill-opacity'] = theme_config['glacier_opacity']
                else:
                    if 'land_fill' in theme_config:
                        paint['fill-color'] = theme_config['land_fill']

        # Apply Buildings
        elif s_layer == 'building':
            if l_type == 'fill':
                paint['fill-color'] = theme_config.get('building_fill', '#dcddde')
                if 'building_outline' in theme_config:
                    paint['fill-outline-color'] = theme_config['building_outline']

        # Apply Transportation (Roads)
        elif s_layer == 'transportation':
            if l_type == 'line':
                is_casing = 'casing' in l_id
                if any(m in l_id for m in ['motorway', 'freeway']):
                    key = 'motorway_casing' if is_casing else 'motorway_fill'
                elif any(m in l_id for m in ['trunk', 'primary']):
                    key = 'primary_casing' if is_casing else 'primary_fill'
                elif any(m in l_id for m in ['secondary']):
                    key = 'secondary_casing' if is_casing else 'secondary_fill'
                elif any(m in l_id for m in ['tertiary', 'minor', 'residential', 'service']):
                    key = 'minor_casing' if is_casing else 'minor_fill'
                elif any(m in l_id for m in ['path', 'pedestrian', 'footway', 'cycleway']):
                    key = 'path_line'
                elif any(m in l_id for m in ['rail', 'transit']):
                    key = 'rail_line'
                else:
                    key = 'minor_casing' if is_casing else 'minor_fill'

                if key in theme_config:
                    paint['line-color'] = theme_config[key]

                if any(m in l_id for m in ['rail', 'transit']) and theme_config.get('rail_width_boost'):
                    paint['line-width'] = [
                        "interpolate",
                        ["exponential", 1.3],
                        ["zoom"],
                        6, 1.8,
                        10, 3.2,
                        14, 5.0
                    ]

                new_layers.append(layer)

                # Add dashed railway ties/ticks if requested
                if l_id == 'railway' and theme_config.get('include_rail_ticks') and not is_ref_only:
                    tick_color = theme_config.get('rail_ticks_color', '#ffffff')
                    new_layers.append({
                        "id": "railway_ticks",
                        "type": "line",
                        "source": "openmaptiles",
                        "source-layer": "transportation",
                        "filter": [
                            "all",
                            ["match", ["geometry-type"], ["LineString", "MultiLineString"], True, False],
                            ["==", ["get", "class"], "rail"]
                        ],
                        "paint": {
                            "line-color": tick_color,
                            "line-width": 1.5,
                            "line-dasharray": [1.5, 1.5]
                        }
                    })
                continue

        # Apply Boundaries
        elif s_layer == 'boundary':
            if l_type == 'line':
                if 'country' in l_id or 'admin_level_2' in l_id or 'admin-2' in l_id:
                    paint['line-color'] = theme_config.get('boundary_country', '#9c9c9c')
                else:
                    paint['line-color'] = theme_config.get('boundary_state', '#b9b9b9')

        # Apply Labels (Symbols)
        elif l_type == 'symbol':
            if theme_config.get('include_uk_shields') and 'shield' in l_id:
                continue

            default_halo = theme_config.get('label_city_halo', theme_config.get('background', '#ffffff'))
            default_subtle_text = theme_config.get('label_road', theme_config.get('label_country', theme_config.get('label_city', '#666666')))

            if s_layer == 'place':
                if any(c in l_id for c in ['city', 'town', 'village']):
                    paint['text-color'] = theme_config.get('label_city', '#333333')
                    if 'label_city_halo' in theme_config:
                        paint['text-halo-color'] = theme_config['label_city_halo']
                        paint['text-halo-width'] = 1.2
                elif any(c in l_id for c in ['country', 'state']):
                    paint['text-color'] = theme_config.get('label_country', '#555555')
                    if 'label_country_halo' in theme_config:
                        paint['text-halo-color'] = theme_config['label_country_halo']
                        paint['text-halo-width'] = 1.5
                else:
                    # Suburbs, neighborhoods, hamlets, quarters (e.g. label_other)
                    paint['text-color'] = theme_config.get('label_other', default_subtle_text)
                    paint['text-halo-color'] = default_halo
                    paint['text-halo-width'] = 1.2

            elif s_layer in ['water_name', 'waterway'] or 'water' in l_id:
                paint['text-color'] = theme_config.get('label_water', '#436fb3')
                if 'label_water_halo' in theme_config:
                    paint['text-halo-color'] = theme_config['label_water_halo']
                    paint['text-halo-width'] = 1.2

            elif s_layer == 'transportation_name':
                if 'shield' not in l_id:
                    paint['text-color'] = theme_config.get('label_road', '#666666')
                    if 'label_road_halo' in theme_config:
                        paint['text-halo-color'] = theme_config['label_road_halo']
                        paint['text-halo-width'] = 1.0

            elif s_layer in ['poi', 'poi_transit'] or 'poi' in l_id:
                paint['text-color'] = theme_config.get('label_poi', default_subtle_text)
                paint['text-halo-color'] = theme_config.get('label_poi_halo', default_halo)
                paint['text-halo-width'] = 1.0

            elif s_layer == 'aerodrome_label' or 'airport' in l_id:
                paint['text-color'] = theme_config.get('label_airport', default_subtle_text)
                paint['text-halo-color'] = default_halo
                paint['text-halo-width'] = 1.0

            else:
                # Catch-all for any other symbol layers (housenumber, etc.)
                if 'text-halo-color' in paint:
                    paint['text-halo-color'] = default_halo
                if 'text-color' in paint:
                    paint['text-color'] = default_subtle_text

        new_layers.append(layer)

    if theme_config.get('include_uk_shields') and not is_base_only:
        uk_shields = [
            {
                "id": "ref_motorway_badge",
                "type": "symbol",
                "source": "openmaptiles",
                "source-layer": "transportation_name",
                "minzoom": 6,
                "filter": [
                    "all",
                    ["==", ["get", "class"], "motorway"],
                    ["has", "ref"]
                ],
                "layout": {
                    "icon-image": "shield_uk_motorway",
                    "icon-text-fit": "both",
                    "icon-text-fit-padding": [2, 5, 2, 5],
                    "icon-optional": True,
                    "text-field": ["to-string", ["get", "ref"]],
                    "text-font": FONT_MAP['bold'],
                    "text-size": 10,
                    "symbol-placement": "line",
                    "text-rotation-alignment": "viewport",
                    "icon-rotation-alignment": "viewport"
                },
                "paint": {
                    "text-color": "#ffffff"
                }
            },
            {
                "id": "ref_primary_a_road_badge",
                "type": "symbol",
                "source": "openmaptiles",
                "source-layer": "transportation_name",
                "minzoom": 7,
                "filter": [
                    "all",
                    ["match", ["get", "class"], ["primary", "trunk"], True, False],
                    ["has", "ref"]
                ],
                "layout": {
                    "icon-image": "shield_uk_primary",
                    "icon-text-fit": "both",
                    "icon-text-fit-padding": [2, 4, 2, 4],
                    "icon-optional": True,
                    "text-field": ["to-string", ["get", "ref"]],
                    "text-font": FONT_MAP['bold'],
                    "text-size": 10,
                    "symbol-placement": "line",
                    "text-rotation-alignment": "viewport",
                    "icon-rotation-alignment": "viewport"
                },
                "paint": {
                    "text-color": "#ffd200"
                }
            },
            {
                "id": "ref_nonprimary_badge",
                "type": "symbol",
                "source": "openmaptiles",
                "source-layer": "transportation_name",
                "minzoom": 9,
                "filter": [
                    "all",
                    ["match", ["get", "class"], ["secondary", "tertiary"], True, False],
                    ["has", "ref"]
                ],
                "layout": {
                    "icon-image": "shield_uk_nonprimary",
                    "icon-text-fit": "both",
                    "icon-text-fit-padding": [2, 4, 2, 4],
                    "icon-optional": True,
                    "text-field": ["to-string", ["get", "ref"]],
                    "text-font": FONT_MAP['bold'],
                    "text-size": 10,
                    "symbol-placement": "line",
                    "text-rotation-alignment": "viewport",
                    "icon-rotation-alignment": "viewport"
                },
                "paint": {
                    "text-color": "#111111"
                }
            },
            {
                "id": "motorway_junction_badge",
                "type": "symbol",
                "source": "openmaptiles",
                "source-layer": "transportation_name",
                "minzoom": 10,
                "filter": [
                    "all",
                    [
                        "any",
                        ["==", ["get", "subclass"], "junction"],
                        ["==", ["get", "class"], "motorway_junction"]
                    ],
                    ["has", "ref"]
                ],
                "layout": {
                    "icon-image": "shield_uk_junction",
                    "icon-text-fit": "both",
                    "icon-text-fit-padding": [2, 4, 2, 4],
                    "icon-optional": True,
                    "text-field": ["to-string", ["get", "ref"]],
                    "text-font": FONT_MAP['bold'],
                    "text-size": 10,
                    "symbol-placement": "point",
                    "text-anchor": "center",
                    "text-rotation-alignment": "viewport",
                    "icon-rotation-alignment": "viewport",
                    "icon-allow-overlap": False,
                    "text-allow-overlap": False
                },
                "paint": {
                    "text-color": "#ffffff",
                    "text-halo-color": "#111111",
                    "text-halo-width": 2
                }
            }
        ]
        new_layers.extend(uk_shields)

    style['layers'] = new_layers
    return style

# Theme Definitions for open-source vector basemaps
THEMES = {
    'light-gray': {
        'name': 'Light Gray Canvas',
        'template': 'bright',
        'background': '#efefef',
        'water_fill': '#cfd3d4',
        'water_outline': '#b8bec0',
        'waterway_line': '#b8bec0',
        'land_fill': {'stops': [[0, '#f4f4f4'], [7, '#efefef']]},
        'wood_fill': {'stops': [[6, '#ECEEEA'], [11, '#e4e8e4']]},
        'park_fill': {'stops': [[6, '#ECEEEA'], [11, '#e4e8e4']]},
        'residential_fill': {'stops': [[5, '#e5e8e7'], [10, '#ecedec']]},
        'commercial_fill': '#ebeeed',
        'industrial_fill': '#e5e8e7',
        'special_fill': '#f2f2f1',
        'sand_fill': '#f0f0ea',
        'building_fill': '#DFE1E2',
        'building_outline': '#efefef',
        'motorway_casing': '#E3E5E2',
        'motorway_fill': {'stops': [[6, '#FAFAFA'], [7, '#ffffff']]},
        'primary_casing': '#E3E5E2',
        'primary_fill': '#ffffff',
        'secondary_casing': '#E3E5E2',
        'secondary_fill': '#ffffff',
        'minor_casing': '#E3E5E2',
        'minor_fill': {'stops': [[12, '#FAFAFA'], [13, '#ffffff']]},
        'path_line': '#ffffff',
        'rail_line': '#dcddda',
        'boundary_country': {'stops': [[5, '#cccccc'], [7, '#9C9C9C']]},
        'boundary_state': {'stops': [[7, '#c8c8c8'], [12, '#b9b9b9']]},
        'label_city': '#353635',
        'label_city_halo': '#efefef',
        'label_country': '#aaafac',
        'label_country_halo': '#f7f7f7',
        'label_water': '#888f91',
        'label_water_halo': '#efefef',
        'label_road': '#7e7e7e',
        'label_road_halo': '#ffffff'
    },

    'dark-gray': {
        'name': 'Dark Gray Canvas',
        'template': 'bright',
        'background': '#252627',
        'water_fill': '#131517',
        'water_outline': '#3a4045',
        'waterway_line': '#4a5359',
        'land_fill': {'stops': [[0, '#2e3032'], [12, '#282a2b'], [15, '#252627']]},
        'wood_fill': {'stops': [[7, '#2a2d2a'], [9, '#2a2d2a']]},
        'park_fill': {'stops': [[7, '#2a2d2a'], [9, '#2a2d2a']]},
        'residential_fill': '#222324',
        'commercial_fill': '#252627',
        'industrial_fill': '#202122',
        'special_fill': '#262728',
        'sand_fill': '#2d2c29',
        'glacier_fill': '#333638',
        'building_fill': '#222324',
        'building_outline': '#36383a',
        'motorway_casing': '#33373a',
        'motorway_fill': '#99a3a8',
        'primary_casing': '#2e3235',
        'primary_fill': '#7d878d',
        'secondary_casing': '#2b2e30',
        'secondary_fill': '#656e73',
        'minor_casing': '#202122',
        'minor_fill': '#4d5458',
        'path_line': '#4d5458',
        'rail_line': '#3a4045',
        'boundary_country': '#70777a',
        'boundary_state': '#505658',
        'label_city': '#e4e8eb',
        'label_city_halo': '#131517',
        'label_country': '#9faab0',
        'label_country_halo': '#131517',
        'label_water': '#7c8e96',
        'label_water_halo': '#131517',
        'label_road': '#8a9499',
        'label_road_halo': '#131517'
    },

    'navigation': {
        'name': 'World Navigation Map',
        'template': 'bright',
        'background': '#f2eee1',
        'water_fill': '#a7d6fe',
        'water_outline': '#72b8f5',
        'waterway_line': '#72b8f5',
        'land_fill': {'stops': [[0, '#f2eee1'], [18, '#fcf2eb']]},
        'wood_fill': '#bdf2af',
        'park_fill': {'stops': [[3, '#e1ecc7'], [8, '#bdf2af']]},
        'residential_fill': {'stops': [[5, '#e9dfd7'], [12, '#f6f0e9']]},
        'commercial_fill': '#ebe5d8',
        'industrial_fill': '#ebe5d8',
        'special_fill': '#f0ede6',
        'sand_fill': '#f5edd6',
        'building_fill': '#bab4a3',
        'building_outline': {'stops': [[15, '#e9e8e8'], [18, '#b6b5b3']]},
        'motorway_casing': {'stops': [[4, '#ffffff'], [5, '#f6be8e'], [8, '#f48c30']]},
        'motorway_fill': {'stops': [[4, '#ffee8b'], [7, '#fae564']]},
        'primary_casing': {'stops': [[8, '#ffffff'], [9, '#f8bd72'], [15, '#f48c30']]},
        'primary_fill': {'stops': [[8, '#ffffff'], [9, '#fff8c8']]},
        'secondary_casing': '#d9d9d9',
        'secondary_fill': '#ffffff',
        'minor_casing': '#dbdbdb',
        'minor_fill': '#ffffff',
        'path_line': '#ffffff',
        'rail_line': '#999999',
        'boundary_country': {'stops': [[0, '#d5d1e3'], [10, '#ada6be']]},
        'boundary_state': '#d4c9eb',
        'label_city': '#333333',
        'label_city_halo': '#ffffff',
        'label_country': '#309730',
        'label_country_halo': '#ffffff',
        'label_water': '#436fb3',
        'label_water_halo': '#ffffff',
        'label_road': '#555555',
        'label_road_halo': '#ffffff'
    },

    'navigation-dark': {
        'name': 'World Navigation Map (Dark)',
        'template': 'bright',
        'background': '#1c1b19',
        'water_fill': '#141c30',
        'water_outline': '#35487a',
        'waterway_line': '#4762a6',
        'land_fill': '#1c1b19',
        'wood_fill': '#21291f',
        'park_fill': '#1e261c',
        'residential_fill': '#1a1917',
        'commercial_fill': '#201e1c',
        'industrial_fill': '#181715',
        'special_fill': '#1e1d1b',
        'sand_fill': '#2e2922',
        'glacier_fill': '#2d2d2c',
        'building_fill': '#2b2a27',
        'building_outline': '#42403b',
        'motorway_casing': '#4a2c0f',
        'motorway_fill': '#f09624',
        'primary_casing': '#3d2e0f',
        'primary_fill': '#deb228',
        'secondary_casing': '#2c2b29',
        'secondary_fill': '#6e6d68',
        'minor_casing': '#1f1e1c',
        'minor_fill': '#4d4c47',
        'path_line': '#54534e',
        'rail_line': '#6b6962',
        'boundary_country': '#827d9e',
        'boundary_state': '#5e5a73',
        'label_city': '#ffffff',
        'label_city_halo': '#141412',
        'label_country': '#a3cfa0',
        'label_country_halo': '#141412',
        'label_water': '#8ba4d9',
        'label_water_halo': '#141c30',
        'label_road': '#c7c7c4',
        'label_road_halo': '#141412'
    },

    'streets': {
        'name': 'World Street Map',
        'template': 'bright',
        'background': '#f7f6d5',
        'water_fill': '#BFD9F2',
        'water_outline': '#8cbde8',
        'waterway_line': '#8cbde8',
        'land_fill': '#f7f6d5',
        'wood_fill': '#dee3bc',
        'park_fill': '#dee3bc',
        'residential_fill': '#ecebc9',
        'commercial_fill': '#ebe9cc',
        'industrial_fill': '#e6e3c8',
        'special_fill': '#eae8c7',
        'sand_fill': '#f7f1d2',
        'building_fill': '#A6A697',
        'building_outline': '#cccccc',
        'motorway_casing': '#B36D54',
        'motorway_fill': {'stops': [[4, '#e6beac'], [6, '#e69973']]},
        'primary_casing': '#C79A46',
        'primary_fill': '#FFC469',
        'secondary_casing': '#d4d4d4',
        'secondary_fill': '#ffffff',
        'minor_casing': '#dbdbdb',
        'minor_fill': '#ffffff',
        'path_line': '#ffffff',
        'rail_line': '#999999',
        'boundary_country': '#877B94',
        'boundary_state': '#A89EAE',
        'label_city': '#333333',
        'label_city_halo': '#f7f6d5',
        'label_country': '#544766',
        'label_country_halo': '#ffffff',
        'label_water': '#326E9C',
        'label_water_halo': '#ffffff',
        'label_road': '#444444',
        'label_road_halo': '#ffffff'
    },

    'streets-night': {
        'name': 'World Street Map (Night)',
        'template': 'bright',
        'background': '#16181c',
        'water_fill': '#0a1524',
        'water_outline': '#1c4573',
        'waterway_line': '#2d6bb3',
        'land_fill': '#16181c',
        'wood_fill': '#1a241d',
        'park_fill': '#1a241d',
        'residential_fill': '#191b20',
        'commercial_fill': '#1c1f24',
        'industrial_fill': '#17191d',
        'special_fill': '#1a1d22',
        'sand_fill': '#262420',
        'glacier_fill': '#22252b',
        'building_fill': '#262930',
        'building_outline': '#3a3f4a',
        'motorway_casing': '#522b0a',
        'motorway_fill': '#eb8923',
        'primary_casing': '#45330a',
        'primary_fill': '#c79d28',
        'secondary_casing': '#252830',
        'secondary_fill': '#5c616e',
        'minor_casing': '#1c1e24',
        'minor_fill': '#444854',
        'path_line': '#4d5261',
        'rail_line': '#5e6475',
        'boundary_country': '#6e6387',
        'boundary_state': '#504863',
        'label_city': '#ffffff',
        'label_city_halo': '#0e1014',
        'label_country': '#baaadb',
        'label_country_halo': '#0e1014',
        'label_water': '#5b98d1',
        'label_water_halo': '#0a1524',
        'label_road': '#b5b9c4',
        'label_road_halo': '#0e1014'
    },

    'topographic': {
        'name': 'World Topographic Map',
        'template': 'bright',
        'include_relief': True,
        'background': '#ecede3',
        'water_fill': '#abe1f6',
        'water_outline': '#7ac2df',
        'waterway_line': '#7ac2df',
        'land_fill': {'stops': [[0, '#e1e3d0'], [8, '#e1e3d0'], [14, '#E1E3D0'], [15, '#ecede3'], [17, '#f1f2ea']]},
        'wood_fill': '#cae4b5',
        'park_fill': '#cae4b5',
        'residential_fill': '#e6e4cb',
        'commercial_fill': '#e8e5cc',
        'industrial_fill': '#dedcc5',
        'special_fill': '#e3e1c6',
        'sand_fill': '#ede5cc',
        'building_fill': '#A6A697',
        'building_outline': '#b5b5a8',
        'motorway_casing': '#c77858',
        'motorway_fill': '#f0a384',
        'primary_casing': '#cca552',
        'primary_fill': '#ffda85',
        'secondary_casing': '#cfcfcf',
        'secondary_fill': '#ffffff',
        'minor_casing': '#dbdbdb',
        'minor_fill': '#ffffff',
        'path_line': '#ffffff',
        'rail_line': '#999999',
        'boundary_country': '#6b577d',
        'boundary_state': '#8b7a9c',
        'label_city': '#262626',
        'label_city_halo': '#ffffff',
        'label_country': '#4d3961',
        'label_country_halo': '#ffffff',
        'label_water': '#21628f',
        'label_water_halo': '#ffffff',
        'label_road': '#444444',
        'label_road_halo': '#ffffff'
    },

    'osm': {
        'name': 'OpenStreetMap (Classic)',
        'template': 'bright',
        'background': '#F2EFE9',
        'water_fill': '#AAD3DF',
        'water_outline': '#7fb4c4',
        'waterway_line': '#7fb4c4',
        'land_fill': '#F2EFE9',
        'wood_fill': '#add19e',
        'park_fill': '#cdebb0',
        'residential_fill': '#e0dfdf',
        'commercial_fill': '#f2dad9',
        'industrial_fill': '#ebdbe8',
        'special_fill': '#ffffd0',
        'sand_fill': '#f5edd6',
        'building_fill': '#d9d0c9',
        'building_outline': '#ccb3a3',
        'motorway_casing': '#dc2a67',
        'motorway_fill': '#e892a2',
        'primary_casing': '#c84e2f',
        'primary_fill': '#fcd6a4',
        'secondary_casing': '#a88600',
        'secondary_fill': '#f7fabf',
        'minor_casing': '#cfcdcd',
        'minor_fill': '#ffffff',
        'path_line': '#999999',
        'rail_line': '#555555',
        'boundary_country': '#2e2585',
        'boundary_state': '#5c54a8',
        'label_city': '#222222',
        'label_city_halo': '#ffffff',
        'label_country': '#111111',
        'label_country_halo': '#ffffff',
        'label_water': '#296377',
        'label_water_halo': '#ffffff',
        'label_road': '#333333',
        'label_road_halo': '#ffffff'
    },

    'os-roads': {
        'name': 'Ordnance Survey - Roads',
        'template': 'bright',
        'background': '#FEFFFF',
        'water_fill': '#D5EFF8',
        'water_outline': '#85CCE3',
        'waterway_line': '#85CCE3',
        'land_fill': '#FEFFFF',
        'wood_fill': '#D1F0CE',
        'park_fill': '#EBF5E5',
        'residential_fill': '#F5F5F3',
        'commercial_fill': '#F2ECE4',
        'industrial_fill': '#EAEAEA',
        'special_fill': '#FDFBE7',
        'sand_fill': '#FFF8D9',
        'building_fill': '#FADAB4',
        'building_outline': '#E8C59B',
        'motorway_casing': '#8F8F8F',
        'motorway_fill': '#06B1CA',
        'primary_casing': '#8F8F8F',
        'primary_fill': '#37C256',
        'secondary_casing': '#8F8F8F',
        'secondary_fill': '#FF889D',
        'minor_casing': '#8F8F8F',
        'minor_fill': '#FEF2B4',
        'path_line': '#00843D',
        'rail_line': '#444444',
        'boundary_country': '#702283',
        'boundary_state': '#9453A3',
        'label_city': '#222222',
        'label_city_halo': '#ffffff',
        'label_country': '#111111',
        'label_country_halo': '#ffffff',
        'label_water': '#006B8F',
        'label_water_halo': '#ffffff',
        'label_road': '#222222',
        'label_road_halo': '#ffffff'
    },

    'streetmap': {
        'name': 'Streetmap UK Classic',
        'template': 'bright',
        'background': '#fcfbf7',
        'water_fill': '#9ed5ea',
        'water_outline': '#6eaec8',
        'waterway_line': '#6eaec8',
        'land_fill': '#fcfbf7',
        'wood_fill': '#d9eec7',
        'park_fill': '#d9eec7',
        'residential_fill': '#f7f4ec',
        'commercial_fill': '#f0ece1',
        'industrial_fill': '#e8e4db',
        'special_fill': '#fdfbe7',
        'sand_fill': '#f7f0d7',
        'building_fill': '#eae4db',
        'building_outline': '#cdc5b9',
        'motorway_casing': '#003b6d',
        'motorway_fill': '#0079c1',
        'primary_casing': '#004d25',
        'primary_fill': '#009a44',
        'secondary_casing': '#8c4400',
        'secondary_fill': '#f59c1a',
        'minor_casing': '#9e9e9e',
        'minor_fill': '#ffffff',
        'path_line': '#e66900',
        'rail_line': '#444444',
        'boundary_country': '#702283',
        'boundary_state': '#9453a3',
        'label_city': '#222222',
        'label_city_halo': '#ffffff',
        'label_country': '#111111',
        'label_country_halo': '#ffffff',
        'label_water': '#176387',
        'label_water_halo': '#ffffff',
        'label_road': '#1b1b1b',
        'label_road_halo': '#ffffff',
        'include_rail_ticks': True,
        'include_uk_shields': True
    },

    'os-outdoor': {
        'name': 'Ordnance Survey - Outdoor',
        'template': 'bright',
        'include_relief': True,
        'background': '#F7FAF5',
        'water_fill': '#A9DDEF',
        'water_outline': '#68BAD6',
        'waterway_line': '#68BAD6',
        'land_fill': '#F7FAF5',
        'wood_fill': '#D1E7C3',
        'park_fill': '#E3F0DB',
        'residential_fill': '#EDEBE3',
        'commercial_fill': '#EDE8DC',
        'industrial_fill': '#E6E4DC',
        'special_fill': '#F3F0E6',
        'sand_fill': '#F9F4DC',
        'building_fill': '#DCD7C6',
        'building_outline': '#C8C2AF',
        'motorway_casing': '#346E7B',
        'motorway_fill': '#4E94A3',
        'primary_casing': '#527A4F',
        'primary_fill': '#73A06F',
        'secondary_casing': '#7D7A73',
        'secondary_fill': '#9F9C93',
        'minor_casing': '#B8B5AD',
        'minor_fill': '#FFFFFF',
        'path_line': '#E66900',
        'rail_line': '#666666',
        'boundary_country': '#8E44AD',
        'boundary_state': '#A569BD',
        'label_city': '#333333',
        'label_city_halo': '#ffffff',
        'label_country': '#222222',
        'label_country_halo': '#ffffff',
        'label_water': '#186480',
        'label_water_halo': '#ffffff',
        'label_road': '#444444',
        'label_road_halo': '#ffffff'
    },

    'os-light': {
        'name': 'Ordnance Survey - Light',
        'template': 'bright',
        'background': '#FAFAF8',
        'water_fill': '#C5CDD0',
        'water_outline': '#9CA7AB',
        'waterway_line': '#9CA7AB',
        'land_fill': '#FAFAF8',
        'wood_fill': '#D8DDD4',
        'park_fill': '#EAEEE7',
        'residential_fill': '#EDEDE8',
        'commercial_fill': '#EBEBE6',
        'industrial_fill': '#E6E6E1',
        'special_fill': '#F2F2EC',
        'sand_fill': '#F0EFE6',
        'building_fill': '#E1E0DB',
        'building_outline': '#D0CFCA',
        'motorway_casing': '#B8BAB6',
        'motorway_fill': '#FFFFFF',
        'primary_casing': '#B8BAB6',
        'primary_fill': '#FFFFFF',
        'secondary_casing': '#C5C7C3',
        'secondary_fill': '#FFFFFF',
        'minor_casing': '#D0D2CE',
        'minor_fill': '#FFFFFF',
        'path_line': '#A8AAA6',
        'rail_line': '#90928E',
        'boundary_country': '#8A8D87',
        'boundary_state': '#A2A69E',
        'label_city': '#555855',
        'label_city_halo': '#ffffff',
        'label_country': '#444644',
        'label_country_halo': '#ffffff',
        'label_water': '#6D7478',
        'label_water_halo': '#ffffff',
        'label_road': '#666966',
        'label_road_halo': '#ffffff'
    },

    'modern-antique': {
        'name': 'Modern Antique',
        'template': 'bright',
        'background': '#eee5d4',
        'water_fill': '#b6cfc8',
        'water_outline': '#8ea69e',
        'waterway_line': '#8ea69e',
        'land_fill': '#eee5d4',
        'wood_fill': '#c8c4a5',
        'park_fill': '#d9d5bc',
        'residential_fill': '#e5dab0',
        'commercial_fill': '#ded2a4',
        'industrial_fill': '#ded2a4',
        'special_fill': '#ded5b8',
        'sand_fill': '#ddd5be',
        'glacier_fill': '#e7decd',
        'building_fill': '#c4beae',
        'building_outline': '#a8a292',
        'motorway_casing': '#5c4c3e',
        'motorway_fill': '#8a755d',
        'primary_casing': '#6e6050',
        'primary_fill': '#9e8e78',
        'secondary_casing': '#8a7d6d',
        'secondary_fill': '#b3a490',
        'minor_casing': '#a89d8e',
        'minor_fill': '#ddd3be',
        'path_line': '#8a755d',
        'rail_line': '#756858',
        'boundary_country': '#5e5245',
        'boundary_state': '#877767',
        'label_city': '#2c251e',
        'label_city_halo': '#eee5d4',
        'label_country': '#473d32',
        'label_country_halo': '#eee5d4',
        'label_water': '#3d5c54',
        'label_water_halo': '#eee5d4',
        'label_road': '#5e5040',
        'label_road_halo': '#eee5d4'
    },

    'newspaper': {
        'name': 'Newspaper',
        'template': 'bright',
        'background': '#faf9f7',
        'water_fill': '#c8ced0',
        'water_outline': '#757f84',
        'waterway_line': '#757f84',
        'land_fill': '#faf9f7',
        'wood_fill': '#d1d1c7',
        'park_fill': '#e2e2da',
        'residential_fill': '#f2f0ec',
        'commercial_fill': '#eceae4',
        'industrial_fill': '#e6e4de',
        'special_fill': '#f5f3ef',
        'sand_fill': '#f0eee8',
        'building_fill': '#404040',
        'building_outline': '#222222',
        'motorway_casing': '#000000',
        'motorway_fill': '#262626',
        'primary_casing': '#222222',
        'primary_fill': '#595959',
        'secondary_casing': '#444444',
        'secondary_fill': '#8c8c8c',
        'minor_casing': '#999999',
        'minor_fill': '#d1d1cd',
        'path_line': '#595959',
        'rail_line': '#000000',
        'boundary_country': '#000000',
        'boundary_state': '#555555',
        'label_city': '#000000',
        'label_city_halo': '#faf9f7',
        'label_country': '#111111',
        'label_country_halo': '#faf9f7',
        'label_water': '#4a5357',
        'label_water_halo': '#faf9f7',
        'label_road': '#333333',
        'label_road_halo': '#faf9f7'
    },

    'nova': {
        'name': 'Nova',
        'template': 'bright',
        'background': '#011222',
        'water_fill': '#000914',
        'water_outline': '#00F0FF',
        'waterway_line': '#00d0e0',
        'land_fill': '#011222',
        'wood_fill': '#012338',
        'park_fill': '#012b45',
        'residential_fill': '#01172b',
        'commercial_fill': '#011c33',
        'industrial_fill': '#011526',
        'special_fill': '#011f38',
        'sand_fill': '#0a2233',
        'glacier_fill': '#082038',
        'building_fill': '#022b40',
        'building_outline': '#007799',
        'motorway_casing': '#004860',
        'motorway_fill': '#00e5ff',
        'primary_casing': '#00384a',
        'primary_fill': '#00b8d4',
        'secondary_casing': '#002735',
        'secondary_fill': '#0097a7',
        'minor_casing': '#001e29',
        'minor_fill': '#006073',
        'path_line': '#00F0FF',
        'rail_line': '#00e5ff',
        'boundary_country': '#165C66',
        'boundary_state': '#0f3e45',
        'label_city': '#B5EFFA',
        'label_city_halo': '#011222',
        'label_country': '#76dff0',
        'label_country_halo': '#011222',
        'label_water': '#00d0e0',
        'label_water_halo': '#011222',
        'label_road': '#64cde0',
        'label_road_halo': '#011222'
    },

    'colored-pencil': {
        'name': 'Colored Pencil',
        'template': 'bright',
        'background': '#fffdf7',
        'water_fill': '#A4E4FF',
        'water_outline': '#5eb9e2',
        'waterway_line': '#5eb9e2',
        'land_fill': '#fffdf7',
        'wood_fill': '#b9e8a5',
        'park_fill': '#f7e879',
        'residential_fill': '#f4eedf',
        'commercial_fill': '#f0e8d3',
        'industrial_fill': '#ebe1c7',
        'special_fill': '#f5eedc',
        'sand_fill': '#fceebb',
        'building_fill': '#e8e3cc',
        'building_outline': '#b8af96',
        'motorway_casing': '#b84e23',
        'motorway_fill': '#e67e51',
        'primary_casing': '#b56921',
        'primary_fill': '#e89f4f',
        'secondary_casing': '#ad7d28',
        'secondary_fill': '#e8bb64',
        'minor_casing': '#c4b793',
        'minor_fill': '#ebdcb9',
        'path_line': '#e67e51',
        'rail_line': '#8c7b64',
        'boundary_country': '#965d38',
        'boundary_state': '#ba8259',
        'label_city': '#c71414',
        'label_city_halo': '#fffdf7',
        'label_country': '#8f2424',
        'label_country_halo': '#fffdf7',
        'label_water': '#1f6f9e',
        'label_water_halo': '#fffdf7',
        'label_road': '#6e5a40',
        'label_road_halo': '#fffdf7'
    },

    'charted-territory': {
        'name': 'Charted Territory',
        'template': 'bright',
        'include_relief': True,
        'background': '#efebdf',
        'water_fill': '#a7c0cb',
        'water_outline': '#6d8f9e',
        'waterway_line': '#6d8f9e',
        'land_fill': '#efebdf',
        'wood_fill': '#85c785',
        'park_fill': '#a7d6a7',
        'residential_fill': '#e3e2d3',
        'commercial_fill': '#dddac7',
        'industrial_fill': '#d4d0bb',
        'special_fill': '#ebe8db',
        'sand_fill': '#e8dfc5',
        'glacier_fill': '#e5dfcb',
        'building_fill': '#8b8b85',
        'building_outline': '#6d6d67',
        'motorway_casing': '#5a171c',
        'motorway_fill': '#922B32',
        'primary_casing': '#782b19',
        'primary_fill': '#b55139',
        'secondary_casing': '#855220',
        'secondary_fill': '#c48647',
        'minor_casing': '#aba28a',
        'minor_fill': '#d6cfb8',
        'path_line': '#922B32',
        'rail_line': '#5c5950',
        'boundary_country': '#736d5e',
        'boundary_state': '#9c9484',
        'label_city': '#1a1917',
        'label_city_halo': '#efebdf',
        'label_country': '#3b3834',
        'label_country_halo': '#efebdf',
        'label_water': '#2c4f5e',
        'label_water_halo': '#efebdf',
        'label_road': '#4d473d',
        'label_road_halo': '#efebdf'
    },

    'midcentury': {
        'name': 'Midcentury',
        'template': 'bright',
        'background': '#F7F4E9',
        'water_fill': '#a2ded8',
        'water_outline': '#5abcb2',
        'waterway_line': '#5abcb2',
        'land_fill': '#F7F4E9',
        'wood_fill': '#BCC27F',
        'park_fill': '#cdd496',
        'residential_fill': '#dbd2b8',
        'commercial_fill': '#d4c9ad',
        'industrial_fill': '#ccc0a3',
        'special_fill': '#ede7d5',
        'sand_fill': '#eadebe',
        'glacier_fill': '#ece5d3',
        'building_fill': '#77746c',
        'building_outline': '#58554e',
        'motorway_casing': '#9c7223',
        'motorway_fill': '#CD9F4A',
        'primary_casing': '#9c4520',
        'primary_fill': '#d97d54',
        'secondary_casing': '#9e6428',
        'secondary_fill': '#e0a667',
        'minor_casing': '#b5b08d',
        'minor_fill': '#ddd9bc',
        'path_line': '#CD9F4A',
        'rail_line': '#666155',
        'boundary_country': '#615b4f',
        'boundary_state': '#8a8271',
        'label_city': '#3e606f',
        'label_city_halo': '#F7F4E9',
        'label_country': '#2e4752',
        'label_country_halo': '#F7F4E9',
        'label_water': '#1d5750',
        'label_water_halo': '#F7F4E9',
        'label_road': '#524c3e',
        'label_road_halo': '#F7F4E9'
    },

    'blueprint': {
        'name': 'Blueprint',
        'template': 'bright',
        'background': '#124971',
        'water_fill': '#0a3352',
        'water_outline': '#749DAF',
        'waterway_line': '#749DAF',
        'land_fill': '#124971',
        'wood_fill': '#175785',
        'park_fill': '#195e91',
        'residential_fill': '#144e78',
        'commercial_fill': '#155380',
        'industrial_fill': '#10446b',
        'special_fill': '#165787',
        'sand_fill': '#1c5f8f',
        'glacier_fill': '#1b5d8f',
        'building_fill': '#185b8c',
        'building_outline': '#CDD5C6',
        'motorway_casing': '#4e7e94',
        'motorway_fill': '#ffffff',
        'primary_casing': '#3c667a',
        'primary_fill': '#cde4f0',
        'secondary_casing': '#2d5669',
        'secondary_fill': '#9ec6db',
        'minor_casing': '#1f4557',
        'minor_fill': '#749DAF',
        'path_line': '#CDD5C6',
        'rail_line': '#ffffff',
        'boundary_country': '#CDD5C6',
        'boundary_state': '#8fa89b',
        'label_city': '#dfe6da',
        'label_city_halo': '#124971',
        'label_country': '#bcd4be',
        'label_country_halo': '#124971',
        'label_water': '#8ec0db',
        'label_water_halo': '#124971',
        'label_road': '#b5d5e5',
        'label_road_halo': '#124971'
    },

    'human-geography': {
        'name': 'Human Geography',
        'template': 'bright',
        'background': '#f7f7f7',
        'water_fill': '#dfe0e2',
        'water_outline': '#b0b2b5',
        'waterway_line': '#b0b2b5',
        'land_fill': '#f7f7f7',
        'wood_fill': '#ededed',
        'park_fill': '#ebebeb',
        'residential_fill': '#f2f2f2',
        'commercial_fill': '#eeeeee',
        'industrial_fill': '#e8e8e8',
        'special_fill': '#f4f4f4',
        'sand_fill': '#f0f0f0',
        'building_fill': '#dcdcdc',
        'building_outline': '#c8c8c8',
        'motorway_casing': '#505050',
        'motorway_fill': '#757575',
        'primary_casing': '#757575',
        'primary_fill': '#9e9e9e',
        'secondary_casing': '#9e9e9e',
        'secondary_fill': '#bcbcbc',
        'minor_casing': '#c2c2c2',
        'minor_fill': '#dedede',
        'path_line': '#a8a8a8',
        'rail_line': '#757575',
        'boundary_country': '#7d7d7d',
        'boundary_state': '#a3a3a3',
        'label_city': '#212121',
        'label_city_halo': '#ffffff',
        'label_country': '#424242',
        'label_country_halo': '#ffffff',
        'label_water': '#595959',
        'label_water_halo': '#ffffff',
        'label_road': '#616161',
        'label_road_halo': '#ffffff'
    },

    'human-geography-dark': {
        'name': 'Human Geography Dark',
        'template': 'bright',
        'background': '#222426',
        'water_fill': '#33363b',
        'water_outline': '#484c54',
        'waterway_line': '#484c54',
        'land_fill': '#222426',
        'wood_fill': '#272a2e',
        'park_fill': '#2a2d32',
        'residential_fill': '#25272a',
        'commercial_fill': '#26292d',
        'industrial_fill': '#232528',
        'special_fill': '#282b2f',
        'sand_fill': '#2b2d30',
        'glacier_fill': '#2e3136',
        'building_fill': '#3a3e45',
        'building_outline': '#4e535c',
        'motorway_casing': '#656a73',
        'motorway_fill': '#adadad',
        'primary_casing': '#545861',
        'primary_fill': '#8a8f99',
        'secondary_casing': '#3f434a',
        'secondary_fill': '#656a73',
        'minor_casing': '#31343a',
        'minor_fill': '#4a4e57',
        'path_line': '#545861',
        'rail_line': '#4a4e57',
        'boundary_country': '#8a8f99',
        'boundary_state': '#656a73',
        'label_city': '#ffffff',
        'label_city_halo': '#222426',
        'label_country': '#d6d9de',
        'label_country_halo': '#222426',
        'label_water': '#9fa5b0',
        'label_water_halo': '#222426',
        'label_road': '#838994',
        'label_road_halo': '#222426'
    },

    'community': {
        'name': 'Community',
        'template': 'bright',
        'background': '#f2eee9',
        'water_fill': '#97d8fa',
        'water_outline': '#6BC4F0',
        'waterway_line': '#6BC4F0',
        'land_fill': '#f2eee9',
        'wood_fill': '#CDDFB3',
        'park_fill': '#d7e8be',
        'residential_fill': '#ECE8E3',
        'commercial_fill': '#e6e0d8',
        'industrial_fill': '#ded7cc',
        'special_fill': '#efebe4',
        'sand_fill': '#f5eed7',
        'building_fill': '#d5d0c7',
        'building_outline': '#bcb5a8',
        'motorway_casing': '#e07a34',
        'motorway_fill': '#ffffff',
        'primary_casing': '#e89e38',
        'primary_fill': '#ffffff',
        'secondary_casing': '#e6be43',
        'secondary_fill': '#ffffff',
        'minor_casing': '#d1ccc2',
        'minor_fill': '#ffffff',
        'path_line': '#739551',
        'rail_line': '#736e63',
        'boundary_country': '#918b82',
        'boundary_state': '#b8b2a8',
        'label_city': '#26231f',
        'label_city_halo': '#ffffff',
        'label_country': '#3b3630',
        'label_country_halo': '#ffffff',
        'label_water': '#1e6894',
        'label_water_halo': '#ffffff',
        'label_road': '#4d473e',
        'label_road_halo': '#ffffff'
    },

    'outdoor': {
        'name': 'Outdoor',
        'template': 'bright',
        'include_relief': True,
        'background': '#F5F1E6',
        'water_fill': '#87d6f2',
        'water_outline': '#52b8dc',
        'waterway_line': '#52b8dc',
        'land_fill': '#F5F1E6',
        'wood_fill': '#b6e3a8',
        'park_fill': '#cceebe',
        'residential_fill': '#ebe5d8',
        'commercial_fill': '#e3dccb',
        'industrial_fill': '#dcd4c1',
        'special_fill': '#eee9de',
        'sand_fill': '#f7f0d7',
        'building_fill': '#d8d2c4',
        'building_outline': '#beb6a2',
        'motorway_casing': '#e06830',
        'motorway_fill': '#ffffff',
        'primary_casing': '#e69032',
        'primary_fill': '#ffffff',
        'secondary_casing': '#e0b83e',
        'secondary_fill': '#ffffff',
        'minor_casing': '#c8c2b4',
        'minor_fill': '#ffffff',
        'path_line': '#82572b',
        'rail_line': '#6e685c',
        'boundary_country': '#635b50',
        'boundary_state': '#8a8174',
        'label_city': '#1f1c19',
        'label_city_halo': '#F5F1E6',
        'label_country': '#332f2a',
        'label_country_halo': '#F5F1E6',
        'label_water': '#176387',
        'label_water_halo': '#F5F1E6',
        'label_road': '#474136',
        'label_road_halo': '#F5F1E6'
    },

    'terrain': {
        'name': 'Terrain',
        'template': 'bright',
        'include_relief': True,
        'background': '#fcfcfa',
        'water_fill': '#cdeafb',
        'water_outline': '#4992d1',
        'waterway_line': '#4992d1',
        'land_fill': '#fcfcfa',
        'wood_fill': '#cce6bb',
        'park_fill': '#d8edd0',
        'residential_fill': '#f0ede6',
        'commercial_fill': '#e8e4db',
        'industrial_fill': '#ded9cf',
        'special_fill': '#f5f3ed',
        'sand_fill': '#f5f0db',
        'building_fill': '#c8c8c8',
        'building_outline': '#a8a8a8',
        'motorway_casing': '#e66a2e',
        'motorway_fill': '#ffffff',
        'primary_casing': '#e89438',
        'primary_fill': '#ffffff',
        'secondary_casing': '#d4aa3b',
        'secondary_fill': '#ffffff',
        'minor_casing': '#c4c4be',
        'minor_fill': '#ffffff',
        'path_line': '#948e82',
        'rail_line': '#666666',
        'boundary_country': '#686b6e',
        'boundary_state': '#94979a',
        'label_city': '#141414',
        'label_city_halo': '#fcfcfa',
        'label_country': '#2e2e2e',
        'label_country_halo': '#fcfcfa',
        'label_water': '#1d578a',
        'label_water_halo': '#fcfcfa',
        'label_road': '#3b3b3b',
        'label_road_halo': '#fcfcfa'
    },

    'oceans': {
        'name': 'Oceans',
        'template': 'bright',
        'background': '#e5dfd3',
        'water_fill': '#a2c8db',
        'water_outline': '#5c8ca6',
        'waterway_line': '#7fa8bd',
        'land_fill': '#e5dfd3',
        'wood_fill': '#d6d0c0',
        'park_fill': '#dbd5c5',
        'residential_fill': '#dfd9cc',
        'commercial_fill': '#d6cfbf',
        'industrial_fill': '#ccc4b2',
        'special_fill': '#e8e3d8',
        'sand_fill': '#ded6be',
        'building_fill': '#b8b2a3',
        'building_outline': '#9c9688',
        'motorway_casing': '#a8a08d',
        'motorway_fill': '#cfc8b8',
        'primary_casing': '#aba392',
        'primary_fill': '#d4cebe',
        'secondary_casing': '#b3ab9a',
        'secondary_fill': '#dbd5c7',
        'minor_casing': '#bab3a3',
        'minor_fill': '#ded9cd',
        'path_line': '#9c9688',
        'rail_line': '#858074',
        'boundary_country': '#756f62',
        'boundary_state': '#999285',
        'label_city': '#4a463d',
        'label_city_halo': '#e5dfd3',
        'label_country': '#3b3831',
        'label_country_halo': '#e5dfd3',
        'label_water': '#1b4359',
        'label_water_halo': '#a2c8db',
        'label_road': '#615b50',
        'label_road_halo': '#e5dfd3'
    },

    'stamen-toner': {
        'name': 'Stamen Toner',
        'template': 'bright',
        'background': '#ffffff',
        'water_fill': '#000000',
        'water_outline': '#000000',
        'waterway_line': '#000000',
        'land_fill': '#ffffff',
        'wood_fill': '#ffffff',
        'park_fill': '#ffffff',
        'residential_fill': '#ffffff',
        'commercial_fill': '#ffffff',
        'industrial_fill': '#ffffff',
        'special_fill': '#ffffff',
        'sand_fill': '#ffffff',
        'building_fill': '#000000',
        'building_outline': '#000000',
        'motorway_casing': '#000000',
        'motorway_fill': '#ffffff',
        'primary_casing': '#000000',
        'primary_fill': '#ffffff',
        'secondary_casing': '#000000',
        'secondary_fill': '#ffffff',
        'minor_casing': '#000000',
        'minor_fill': '#ffffff',
        'path_line': '#000000',
        'rail_line': '#000000',
        'include_rail_ticks': True,
        'rail_ticks_color': '#ffffff',
        'boundary_country': '#000000',
        'boundary_state': '#000000',
        'label_city': '#000000',
        'label_city_halo': '#ffffff',
        'label_country': '#000000',
        'label_country_halo': '#ffffff',
        'label_water': '#ffffff',
        'label_water_halo': '#000000',
        'label_road': '#000000',
        'label_road_halo': '#ffffff'
    },

    'carto-voyager': {
        'name': 'CARTO Voyager',
        'template': 'bright',
        'background': '#f4f3ee',
        'water_fill': '#c4e1f7',
        'water_outline': '#a0ccf0',
        'waterway_line': '#a0ccf0',
        'land_fill': '#f4f3ee',
        'wood_fill': '#d8ebd5',
        'park_fill': '#dcf0db',
        'residential_fill': '#ece7de',
        'commercial_fill': '#ede9df',
        'industrial_fill': '#e5e0d5',
        'special_fill': '#eae4d8',
        'sand_fill': '#faecc9',
        'building_fill': '#e3ded4',
        'building_outline': '#d3ccc0',
        'motorway_casing': '#e88b38',
        'motorway_fill': '#ffb559',
        'primary_casing': '#e89a4a',
        'primary_fill': '#ffc778',
        'secondary_casing': '#c9c5bd',
        'secondary_fill': '#ffffff',
        'minor_casing': '#d6d2c8',
        'minor_fill': '#ffffff',
        'path_line': '#abb5a8',
        'rail_line': '#a6a6a6',
        'include_rail_ticks': True,
        'boundary_country': '#767b7e',
        'boundary_state': '#9fa4a7',
        'label_city': '#383f45',
        'label_city_halo': '#fdfdfc',
        'label_country': '#61696e',
        'label_country_halo': '#f4f3ee',
        'label_water': '#36729e',
        'label_water_halo': '#f4f3ee',
        'label_road': '#525a5f',
        'label_road_halo': '#ffffff'
    },

    'google-maps': {
        'name': 'Google Maps (Warm 2014–2023)',
        'template': 'bright',
        'background': '#f4f3f0',
        'water_fill': '#aad3df',
        'water_outline': '#88c0d4',
        'waterway_line': '#88c0d4',
        'land_fill': '#f4f3f0',
        'wood_fill': '#cdebd4',
        'park_fill': '#cceada',
        'residential_fill': '#f0ede8',
        'commercial_fill': '#ece7df',
        'industrial_fill': '#ece6db',
        'special_fill': '#ede7dc',
        'sand_fill': '#faeecd',
        'building_fill': '#eae5dc',
        'building_outline': '#ded7cc',
        'motorway_casing': '#f9b959',
        'motorway_fill': '#fed876',
        'primary_casing': '#fbc97f',
        'primary_fill': '#ffe599',
        'secondary_casing': '#e8e4dc',
        'secondary_fill': '#ffffff',
        'minor_casing': '#e5e1d8',
        'minor_fill': '#ffffff',
        'path_line': '#c6d1c4',
        'rail_line': '#b8b8b8',
        'boundary_country': '#9b9b9b',
        'boundary_state': '#b5b5b5',
        'label_city': '#3c4043',
        'label_city_halo': '#f8f7f5',
        'label_country': '#5f6368',
        'label_country_halo': '#ffffff',
        'label_water': '#336799',
        'label_water_halo': '#ffffff',
        'label_road': '#494c4e',
        'label_road_halo': '#ffffff'
    },

    'google-maps-modern': {
        'name': 'Google Maps (2023+ Cool Slate)',
        'template': 'bright',
        'background': '#e8eaed',
        'water_fill': '#85c9d6',
        'water_outline': '#68aab8',
        'waterway_line': '#68aab8',
        'land_fill': '#e8eaed',
        'wood_fill': '#a8dab5',
        'park_fill': '#a8dab5',
        'residential_fill': '#e3e7ea',
        'commercial_fill': '#dee2e6',
        'industrial_fill': '#dee1e5',
        'special_fill': '#e0e4e8',
        'sand_fill': '#faeed2',
        'building_fill': '#d7d9dc',
        'building_outline': '#c8cbce',
        'motorway_casing': '#435260',
        'motorway_fill': '#596b79',
        'primary_casing': '#6c7c8c',
        'primary_fill': '#8192a2',
        'secondary_casing': '#b0bac2',
        'secondary_fill': '#d3dbe2',
        'minor_casing': '#d5dadf',
        'minor_fill': '#ffffff',
        'path_line': '#b8c5b5',
        'rail_line': '#9ba5ad',
        'boundary_country': '#8c969e',
        'boundary_state': '#a6b0b8',
        'label_city': '#202124',
        'label_city_halo': '#ffffff',
        'label_country': '#5f6368',
        'label_country_halo': '#ffffff',
        'label_water': '#27606e',
        'label_water_halo': '#ffffff',
        'label_road': '#3c4043',
        'label_road_halo': '#ffffff'
    },

    'google-maps-2009': {
        'name': 'Google Maps (Pastel 2009–2013)',
        'template': 'bright',
        'background': '#f5f5f3',
        'water_fill': '#b5d0d0',
        'water_outline': '#9ec0c0',
        'waterway_line': '#9ec0c0',
        'land_fill': '#f5f5f3',
        'wood_fill': '#cae8be',
        'park_fill': '#cae8be',
        'residential_fill': '#f0ede6',
        'commercial_fill': '#edeae1',
        'industrial_fill': '#e8e5dc',
        'special_fill': '#edeae1',
        'sand_fill': '#faecc9',
        'building_fill': '#e8e5dc',
        'building_outline': '#dad5c9',
        'motorway_casing': '#e5aa38',
        'motorway_fill': '#fbd16c',
        'primary_casing': '#e3c574',
        'primary_fill': '#fff5a6',
        'secondary_casing': '#dcdad6',
        'secondary_fill': '#ffffff',
        'minor_casing': '#e2e0dc',
        'minor_fill': '#ffffff',
        'path_line': '#c0d6b6',
        'rail_line': '#888888',
        'boundary_country': '#888888',
        'boundary_state': '#aaaaaa',
        'label_city': '#222222',
        'label_city_halo': '#ffffff',
        'label_country': '#555555',
        'label_country_halo': '#ffffff',
        'label_water': '#447788',
        'label_water_halo': '#ffffff',
        'label_road': '#444444',
        'label_road_halo': '#ffffff'
    },

    'google-maps-retro': {
        'name': 'Google Maps (Classic 2005–2009)',
        'template': 'bright',
        'background': '#ebe6dc',
        'water_fill': '#99b3cc',
        'water_outline': '#7a9bb8',
        'waterway_line': '#7a9bb8',
        'land_fill': '#ebe6dc',
        'wood_fill': '#a7cc95',
        'park_fill': '#a7cc95',
        'residential_fill': '#e6e1d7',
        'commercial_fill': '#ded9ce',
        'industrial_fill': '#d6d1c6',
        'special_fill': '#ded9ce',
        'sand_fill': '#faecc9',
        'building_fill': '#ded6c5',
        'building_outline': '#bfbbb3',
        'motorway_casing': '#c48a00',
        'motorway_fill': '#f2bf24',
        'primary_casing': '#d49b00',
        'primary_fill': '#fffa73',
        'secondary_casing': '#afaba7',
        'secondary_fill': '#ffffff',
        'minor_casing': '#afaba7',
        'minor_fill': '#ffffff',
        'path_line': '#8a9e80',
        'rail_line': '#444444',
        'include_rail_ticks': True,
        'rail_ticks_color': '#ffffff',
        'boundary_country': '#666666',
        'boundary_state': '#888888',
        'label_city': '#000000',
        'label_city_halo': '#ffffff',
        'label_country': '#333333',
        'label_country_halo': '#ffffff',
        'label_water': '#2b5278',
        'label_water_halo': '#ffffff',
        'label_road': '#111111',
        'label_road_halo': '#ffffff'
    },

    'mapquest-classic': {
        'name': 'MapQuest Classic (1996–2004)',
        'template': 'bright',
        'background': '#ffffff',
        'water_fill': '#66ccff',
        'water_outline': '#3399cc',
        'waterway_line': '#3399cc',
        'land_fill': '#ffffff',
        'wood_fill': '#99cc99',
        'park_fill': '#99cc99',
        'residential_fill': '#ffffff',
        'commercial_fill': '#f7f7f7',
        'industrial_fill': '#eeeeee',
        'special_fill': '#ddffdd',
        'sand_fill': '#ffffcc',
        'building_fill': '#dddddd',
        'building_outline': '#bbbbbb',
        'motorway_casing': '#000000',
        'motorway_fill': '#ff9900',
        'primary_casing': '#222222',
        'primary_fill': '#ffff00',
        'secondary_casing': '#444444',
        'secondary_fill': '#ffffff',
        'minor_casing': '#888888',
        'minor_fill': '#ffffff',
        'path_line': '#669966',
        'rail_line': '#000000',
        'include_rail_ticks': True,
        'rail_ticks_color': '#ffffff',
        'boundary_country': '#cc0000',
        'boundary_state': '#cc0000',
        'label_city': '#000000',
        'label_city_halo': '#ffffff',
        'label_country': '#000000',
        'label_country_halo': '#ffffff',
        'label_water': '#003399',
        'label_water_halo': '#ffffff',
        'label_road': '#000000',
        'label_road_halo': '#ffffff'
    },

    'here-classic': {
        'name': 'HERE Maps / Nokia (Classic)',
        'template': 'bright',
        'background': '#f3f3f1',
        'water_fill': '#7ec7e8',
        'water_outline': '#54a6cf',
        'waterway_line': '#54a6cf',
        'land_fill': '#f3f3f1',
        'wood_fill': '#c3e7be',
        'park_fill': '#d1ebd0',
        'residential_fill': '#eceae4',
        'commercial_fill': '#e5e2db',
        'industrial_fill': '#dedad2',
        'special_fill': '#e5e2db',
        'sand_fill': '#faeed5',
        'building_fill': '#dedede',
        'building_outline': '#cacaca',
        'motorway_casing': '#c9540e',
        'motorway_fill': '#ff7b24',
        'primary_casing': '#c48606',
        'primary_fill': '#ffb81c',
        'secondary_casing': '#cac4b7',
        'secondary_fill': '#fbf9f4',
        'minor_casing': '#dedad0',
        'minor_fill': '#ffffff',
        'path_line': '#95b390',
        'rail_line': '#687178',
        'boundary_country': '#63707c',
        'boundary_state': '#8895a1',
        'label_city': '#1c2833',
        'label_city_halo': '#ffffff',
        'label_country': '#415160',
        'label_country_halo': '#ffffff',
        'label_water': '#21618c',
        'label_water_halo': '#ffffff',
        'label_road': '#2c3e50',
        'label_road_halo': '#ffffff'
    },

    'apple-maps': {
        'name': 'Apple Maps',
        'template': 'bright',
        'background': '#f7f6f2',
        'water_fill': '#9ed4fc',
        'water_outline': '#7bc1f7',
        'waterway_line': '#7bc1f7',
        'land_fill': '#f7f6f2',
        'wood_fill': '#d0eed5',
        'park_fill': '#d4eed8',
        'residential_fill': '#f4f2ec',
        'commercial_fill': '#eeebe3',
        'industrial_fill': '#ebe7de',
        'special_fill': '#ede9e0',
        'sand_fill': '#faeed2',
        'building_fill': '#ebe7de',
        'building_outline': '#ded9cf',
        'motorway_casing': '#ea9f47',
        'motorway_fill': '#ffb852',
        'primary_casing': '#e3be5b',
        'primary_fill': '#fedb68',
        'secondary_casing': '#dedbcf',
        'secondary_fill': '#ffffff',
        'minor_casing': '#e6e3d8',
        'minor_fill': '#ffffff',
        'path_line': '#bccdbd',
        'rail_line': '#b4b2ac',
        'boundary_country': '#8e8d89',
        'boundary_state': '#b1b0ab',
        'label_city': '#1c1c1e',
        'label_city_halo': '#fbfaf7',
        'label_country': '#48484a',
        'label_country_halo': '#f7f6f2',
        'label_water': '#2c6ea6',
        'label_water_halo': '#f7f6f2',
        'label_road': '#3a3a3c',
        'label_road_halo': '#ffffff'
    },

    'bing-maps': {
        'name': 'Bing Maps',
        'template': 'bright',
        'background': '#ede9e1',
        'water_fill': '#b2d6f0',
        'water_outline': '#8ac1eb',
        'waterway_line': '#8ac1eb',
        'land_fill': '#ede9e1',
        'wood_fill': '#c4e3c1',
        'park_fill': '#cde8ca',
        'residential_fill': '#e6e0d5',
        'commercial_fill': '#e0dacd',
        'industrial_fill': '#dad4c5',
        'special_fill': '#ded7c8',
        'sand_fill': '#faeed2',
        'building_fill': '#dfd9cc',
        'building_outline': '#cdc5b5',
        'motorway_casing': '#d9a04a',
        'motorway_fill': '#ffcf66',
        'primary_casing': '#d6b665',
        'primary_fill': '#ffe68a',
        'secondary_casing': '#c7c1b4',
        'secondary_fill': '#ffffff',
        'minor_casing': '#d4cdbf',
        'minor_fill': '#ffffff',
        'path_line': '#b3bfae',
        'rail_line': '#a19b8f',
        'boundary_country': '#78736a',
        'boundary_state': '#9e988e',
        'label_city': '#2b2926',
        'label_city_halo': '#f4f2ec',
        'label_country': '#4a4640',
        'label_country_halo': '#f4f2ec',
        'label_water': '#2d6994',
        'label_water_halo': '#f4f2ec',
        'label_road': '#4d4942',
        'label_road_halo': '#ffffff'
    },

    'michelin': {
        'name': 'Michelin Road Atlas',
        'template': 'bright',
        'background': '#fdfdfd',
        'water_fill': '#9bcbee',
        'water_outline': '#6faedd',
        'waterway_line': '#6faedd',
        'land_fill': '#fdfdfd',
        'wood_fill': '#b7e3b5',
        'park_fill': '#c4eac3',
        'residential_fill': '#f5f4ef',
        'commercial_fill': '#eceae2',
        'industrial_fill': '#e4e2d8',
        'special_fill': '#eceae2',
        'sand_fill': '#fcf1d4',
        'building_fill': '#e6decb',
        'building_outline': '#cdbfab',
        'motorway_casing': '#b5181b',
        'motorway_fill': '#e8282b',
        'primary_casing': '#cf2024',
        'primary_fill': '#f03a3d',
        'secondary_casing': '#d99b00',
        'secondary_fill': '#ffd800',
        'minor_casing': '#a3a3a3',
        'minor_fill': '#ffffff',
        'path_line': '#73a167',
        'rail_line': '#4d4d4d',
        'include_rail_ticks': True,
        'boundary_country': '#b5181b',
        'boundary_state': '#e8282b',
        'label_city': '#1a1a1a',
        'label_city_halo': '#ffffff',
        'label_country': '#800d0f',
        'label_country_halo': '#ffffff',
        'label_water': '#165887',
        'label_water_halo': '#ffffff',
        'label_road': '#262626',
        'label_road_halo': '#ffffff'
    },

    'aa-atlas': {
        'name': 'AA Road Atlas (UK)',
        'template': 'bright',
        'include_uk_shields': True,
        'background': '#f8f7f2',
        'water_fill': '#96cae9',
        'water_outline': '#62a6d1',
        'waterway_line': '#62a6d1',
        'land_fill': '#f8f7f2',
        'wood_fill': '#c1e5ba',
        'park_fill': '#cbebc5',
        'residential_fill': '#eee9df',
        'commercial_fill': '#e4ded2',
        'industrial_fill': '#dad3c5',
        'special_fill': '#e4ded2',
        'sand_fill': '#f5e9c9',
        'building_fill': '#f6c492',
        'building_outline': '#d99f69',
        'motorway_casing': '#004578',
        'motorway_fill': '#006cb8',
        'primary_casing': '#005026',
        'primary_fill': '#007a3d',
        'secondary_casing': '#c77f00',
        'secondary_fill': '#fbb900',
        'minor_casing': '#8c8c8c',
        'minor_fill': '#ffffff',
        'path_line': '#649658',
        'rail_line': '#383838',
        'include_rail_ticks': True,
        'boundary_country': '#2b2b2b',
        'boundary_state': '#5e5e5e',
        'label_city': '#111111',
        'label_city_halo': '#f8f7f2',
        'label_country': '#1f384f',
        'label_country_halo': '#ffffff',
        'label_water': '#134e73',
        'label_water_halo': '#ffffff',
        'label_road': '#111111',
        'label_road_halo': '#ffffff'
    },

    'rand-mcnally': {
        'name': 'Rand McNally Road Atlas',
        'template': 'bright',
        'background': '#faf7ed',
        'water_fill': '#9bc5df',
        'water_outline': '#6a9ebf',
        'waterway_line': '#6a9ebf',
        'land_fill': '#faf7ed',
        'wood_fill': '#c4e3be',
        'park_fill': '#bfe2b8',
        'residential_fill': '#f0ebdc',
        'commercial_fill': '#e5decb',
        'industrial_fill': '#dbd3be',
        'special_fill': '#e3dbc6',
        'sand_fill': '#faebd2',
        'building_fill': '#ded6c3',
        'building_outline': '#c7bc9f',
        'motorway_casing': '#0a3359',
        'motorway_fill': '#135896',
        'primary_casing': '#9e181c',
        'primary_fill': '#d8282e',
        'secondary_casing': '#a37a1f',
        'secondary_fill': '#f0b52d',
        'minor_casing': '#8a8a8a',
        'minor_fill': '#ffffff',
        'path_line': '#698c62',
        'rail_line': '#404040',
        'include_rail_ticks': True,
        'boundary_country': '#782b3d',
        'boundary_state': '#9e4458',
        'label_city': '#141414',
        'label_city_halo': '#faf7ed',
        'label_country': '#4a1824',
        'label_country_halo': '#ffffff',
        'label_water': '#164669',
        'label_water_halo': '#faf7ed',
        'label_road': '#292929',
        'label_road_halo': '#ffffff'
    },

    'os-landranger': {
        'name': 'Ordnance Survey Landranger (1:50k)',
        'template': 'bright',
        'include_uk_shields': True,
        'background': '#faf8f2',
        'water_fill': '#87ceeb',
        'water_outline': '#4682b4',
        'waterway_line': '#4682b4',
        'land_fill': '#faf8f2',
        'wood_fill': '#c1deb1',
        'park_fill': '#d2ebd0',
        'residential_fill': '#f0e6e6',
        'commercial_fill': '#ebdcdc',
        'industrial_fill': '#e2dede',
        'special_fill': '#ebdcdc',
        'sand_fill': '#fff5cc',
        'glacier_fill': '#eef2f5',
        'building_fill': '#d4c2b8',
        'building_outline': '#b8a599',
        'motorway_casing': '#004e8c',
        'motorway_fill': '#0078d7',
        'primary_casing': '#990045',
        'primary_fill': '#e60067',
        'secondary_casing': '#cc5500',
        'secondary_fill': '#ff7700',
        'minor_casing': '#baa130',
        'minor_fill': '#ffea6c',
        'path_line': '#2e8b57',
        'rail_line': '#000000',
        'include_rail_ticks': True,
        'rail_ticks_color': '#ffffff',
        'boundary_country': '#8b0000',
        'boundary_state': '#a52a2a',
        'label_city': '#111111',
        'label_city_halo': '#faf8f2',
        'label_country': '#222222',
        'label_country_halo': '#faf8f2',
        'label_water': '#004e8c',
        'label_water_halo': '#faf8f2',
        'label_road': '#111111',
        'label_road_halo': '#ffffff'
    },

    'swisstopo': {
        'name': 'Swisstopo (Swiss National Map)',
        'template': 'bright',
        'include_relief': True,
        'background': '#faf8f3',
        'water_fill': '#a0c8e6',
        'water_outline': '#739ebb',
        'waterway_line': '#739ebb',
        'land_fill': '#faf8f3',
        'wood_fill': '#c5e1be',
        'park_fill': '#d7ebd2',
        'residential_fill': '#eeebe3',
        'commercial_fill': '#eae5dc',
        'industrial_fill': '#e4ded4',
        'special_fill': '#eae5dc',
        'sand_fill': '#f7f0df',
        'glacier_fill': '#edf4fa',
        'building_fill': '#ded5c4',
        'building_outline': '#a69f92',
        'motorway_casing': '#9e1c1c',
        'motorway_fill': '#dd352e',
        'primary_casing': '#b36600',
        'primary_fill': '#f59c16',
        'secondary_casing': '#baa13b',
        'secondary_fill': '#fce277',
        'minor_casing': '#9c9c9c',
        'minor_fill': '#ffffff',
        'path_line': '#7a7063',
        'rail_line': '#333333',
        'include_rail_ticks': True,
        'rail_ticks_color': '#ffffff',
        'boundary_country': '#444444',
        'boundary_state': '#777777',
        'label_city': '#111111',
        'label_city_halo': '#faf8f3',
        'label_country': '#222222',
        'label_country_halo': '#faf8f3',
        'label_water': '#2c5f85',
        'label_water_halo': '#faf8f3',
        'label_road': '#222222',
        'label_road_halo': '#ffffff'
    },

    'natgeo': {
        'name': 'National Geographic Atlas',
        'template': 'bright',
        'include_relief': True,
        'background': '#f0e8d5',
        'water_fill': '#b0cbdc',
        'water_outline': '#749db7',
        'waterway_line': '#749db7',
        'land_fill': '#f0e8d5',
        'wood_fill': '#c9d9be',
        'park_fill': '#cedec4',
        'residential_fill': '#e5dcbe',
        'commercial_fill': '#ded4b4',
        'industrial_fill': '#d6cca7',
        'special_fill': '#ded4b4',
        'sand_fill': '#e8deb8',
        'glacier_fill': '#e6dcbf',
        'building_fill': '#d9ceb0',
        'building_outline': '#beb395',
        'motorway_casing': '#b56038',
        'motorway_fill': '#db8056',
        'primary_casing': '#bf8b43',
        'primary_fill': '#e8ad5a',
        'secondary_casing': '#ad977b',
        'secondary_fill': '#ffffff',
        'minor_casing': '#baa891',
        'minor_fill': '#ffffff',
        'path_line': '#829978',
        'rail_line': '#706654',
        'include_rail_ticks': True,
        'boundary_country': '#9c4149',
        'boundary_state': '#a86b5b',
        'label_city': '#2b271d',
        'label_city_halo': '#f0e8d5',
        'label_country': '#542817',
        'label_country_halo': '#f0e8d5',
        'label_water': '#264e66',
        'label_water_halo': '#f0e8d5',
        'label_road': '#473e31',
        'label_road_halo': '#ffffff'
    },

    'os-zoomstack-night': {
        'name': 'Ordnance Survey - Night',
        'template': 'bright',
        'background': '#0f1721',
        'water_fill': '#070d14',
        'water_outline': '#1f5b8a',
        'waterway_line': '#2b7dbd',
        'land_fill': '#0f1721',
        'wood_fill': '#14202d',
        'park_fill': '#162332',
        'residential_fill': '#121b27',
        'commercial_fill': '#141e2b',
        'industrial_fill': '#101721',
        'special_fill': '#131d2a',
        'sand_fill': '#1d232a',
        'glacier_fill': '#1c2837',
        'building_fill': '#1a2737',
        'building_outline': '#2b3f57',
        'motorway_casing': '#006d7a',
        'motorway_fill': '#00f2ff',
        'primary_casing': '#994400',
        'primary_fill': '#ff8000',
        'secondary_casing': '#996e00',
        'secondary_fill': '#ffbb00',
        'minor_casing': '#1f2e3d',
        'minor_fill': '#425a75',
        'path_line': '#486382',
        'rail_line': '#5c7b9e',
        'boundary_country': '#7fa3c4',
        'boundary_state': '#527291',
        'label_city': '#ffffff',
        'label_city_halo': '#0a1017',
        'label_country': '#a3cbef',
        'label_country_halo': '#070d14',
        'label_water': '#5bb3f0',
        'label_water_halo': '#070d14',
        'label_road': '#cde2f5',
        'label_road_halo': '#0f1721'
    },

    'os-deuteranopia': {
        'name': 'Ordnance Survey - Deuteranopia (Accessible)',
        'template': 'bright',
        'background': '#f4f3ed',
        'water_fill': '#9ecae1',
        'water_outline': '#6baed6',
        'waterway_line': '#6baed6',
        'land_fill': '#f4f3ed',
        'wood_fill': '#dadaeb',
        'park_fill': '#bcbddc',
        'residential_fill': '#edebe1',
        'commercial_fill': '#e4e1d5',
        'industrial_fill': '#dbd7c9',
        'special_fill': '#e2ded0',
        'sand_fill': '#fee6ce',
        'building_fill': '#d2cedb',
        'building_outline': '#b7b2c2',
        'motorway_casing': '#542788',
        'motorway_fill': '#8073ac',
        'primary_casing': '#08519c',
        'primary_fill': '#3182bd',
        'secondary_casing': '#b27700',
        'secondary_fill': '#fec44f',
        'minor_casing': '#969696',
        'minor_fill': '#ffffff',
        'path_line': '#756bb1',
        'rail_line': '#525252',
        'include_rail_ticks': True,
        'boundary_country': '#252525',
        'boundary_state': '#636363',
        'label_city': '#1c1c1c',
        'label_city_halo': '#f4f3ed',
        'label_country': '#3f007d',
        'label_country_halo': '#ffffff',
        'label_water': '#08519c',
        'label_water_halo': '#ffffff',
        'label_road': '#252525',
        'label_road_halo': '#ffffff'
    },

    'os-tritanopia': {
        'name': 'Ordnance Survey - Tritanopia (Accessible)',
        'template': 'bright',
        'background': '#f7f4f2',
        'water_fill': '#b8e2de',
        'water_outline': '#7bc4be',
        'waterway_line': '#7bc4be',
        'land_fill': '#f7f4f2',
        'wood_fill': '#d1e8e2',
        'park_fill': '#c4e3dc',
        'residential_fill': '#eee7e3',
        'commercial_fill': '#e5dcd6',
        'industrial_fill': '#dcd1ca',
        'special_fill': '#e3d8d1',
        'sand_fill': '#e8ded6',
        'building_fill': '#e0d3ce',
        'building_outline': '#c7b6b0',
        'motorway_casing': '#8c1d40',
        'motorway_fill': '#c23b63',
        'primary_casing': '#006660',
        'primary_fill': '#008f86',
        'secondary_casing': '#b85933',
        'secondary_fill': '#e07a4a',
        'minor_casing': '#948b87',
        'minor_fill': '#ffffff',
        'path_line': '#006660',
        'rail_line': '#47423f',
        'include_rail_ticks': True,
        'boundary_country': '#38111e',
        'boundary_state': '#5e2d3b',
        'label_city': '#241e1c',
        'label_city_halo': '#f7f4f2',
        'label_country': '#5e182e',
        'label_country_halo': '#ffffff',
        'label_water': '#004d47',
        'label_water_halo': '#ffffff',
        'label_road': '#2e2927',
        'label_road_halo': '#ffffff'
    },

    'humanitarian': {
        'name': 'Humanitarian (HOT)',
        'template': 'bright',
        'background': '#f2efe9',
        'water_fill': '#b5d0d0',
        'water_outline': '#83adad',
        'waterway_line': '#83adad',
        'land_fill': '#f2efe9',
        'wood_fill': '#c8df9f',
        'park_fill': '#cee4a6',
        'residential_fill': '#ece6df',
        'commercial_fill': '#e4ded4',
        'industrial_fill': '#dbd4c7',
        'special_fill': '#ffcfd8',
        'sand_fill': '#faecc9',
        'building_fill': '#d9d0c7',
        'building_outline': '#bfb5ab',
        'motorway_casing': '#b33b43',
        'motorway_fill': '#e46d74',
        'primary_casing': '#cc6633',
        'primary_fill': '#f29c66',
        'secondary_casing': '#cca333',
        'secondary_fill': '#f7d16d',
        'minor_casing': '#b8b8b8',
        'minor_fill': '#ffffff',
        'path_line': '#7fa867',
        'rail_line': '#4a4a4a',
        'include_rail_ticks': True,
        'boundary_country': '#6e3b5e',
        'boundary_state': '#996188',
        'label_city': '#262626',
        'label_city_halo': '#f2efe9',
        'label_country': '#4a273f',
        'label_country_halo': '#ffffff',
        'label_water': '#1f5959',
        'label_water_halo': '#ffffff',
        'label_road': '#333333',
        'label_road_halo': '#ffffff'
    },

    'transport-transit': {
        'name': 'Thunderforest Transport (Transit)',
        'template': 'bright',
        'rail_width_boost': True,
        'background': '#f6f5f2',
        'water_fill': '#cbe2f2',
        'water_outline': '#a4cbe6',
        'waterway_line': '#a4cbe6',
        'land_fill': '#f6f5f2',
        'wood_fill': '#e3ede1',
        'park_fill': '#e6f0e4',
        'residential_fill': '#f0eee9',
        'commercial_fill': '#ebe8e1',
        'industrial_fill': '#e4e0d7',
        'special_fill': '#ede8df',
        'sand_fill': '#f7f0df',
        'building_fill': '#e8e4dc',
        'building_outline': '#d9d4c7',
        'motorway_casing': '#d9d5cb',
        'motorway_fill': '#ede9df',
        'primary_casing': '#d9d5cb',
        'primary_fill': '#ede9df',
        'secondary_casing': '#dedbd3',
        'secondary_fill': '#f2eee6',
        'minor_casing': '#e6e3dc',
        'minor_fill': '#ffffff',
        'path_line': '#dedbd3',
        'rail_line': '#d9381e',
        'include_rail_ticks': True,
        'rail_ticks_color': '#ffffff',
        'boundary_country': '#9c9689',
        'boundary_state': '#b8b2a5',
        'label_city': '#3b3834',
        'label_city_halo': '#f6f5f2',
        'label_country': '#6e6961',
        'label_country_halo': '#ffffff',
        'label_water': '#3b6d8c',
        'label_water_halo': '#ffffff',
        'label_road': '#8c877e',
        'label_road_halo': '#ffffff'
    },

    'osm-carto': {
        'name': 'OpenStreetMap Standard (OSM Carto)',
        'template': 'bright',
        'background': '#f2efe9',
        'water_fill': '#aad3df',
        'water_outline': '#84b5c4',
        'waterway_line': '#84b5c4',
        'land_fill': '#f2efe9',
        'wood_fill': '#add19e',
        'park_fill': '#c8facc',
        'residential_fill': '#e0dfdf',
        'commercial_fill': '#f2dad9',
        'industrial_fill': '#dfd1d6',
        'special_fill': '#ebe6e6',
        'sand_fill': '#f5e9c6',
        'building_fill': '#d9d0c9',
        'building_outline': '#bfb5ad',
        'motorway_casing': '#c24e6b',
        'motorway_fill': '#e990a0',
        'primary_casing': '#d48011',
        'primary_fill': '#fdbf6f',
        'secondary_casing': '#caa338',
        'secondary_fill': '#f7fabf',
        'minor_casing': '#cfcfcf',
        'minor_fill': '#ffffff',
        'path_line': '#999999',
        'rail_line': '#777777',
        'include_rail_ticks': True,
        'rail_ticks_color': '#ffffff',
        'boundary_country': '#7b68ee',
        'boundary_state': '#9370db',
        'label_city': '#000000',
        'label_city_halo': '#ffffff',
        'label_country': '#4b0082',
        'label_country_halo': '#ffffff',
        'label_water': '#336699',
        'label_water_halo': '#ffffff',
        'label_road': '#333333',
        'label_road_halo': '#ffffff'
    },

    'monochrome-indigo': {
        'name': 'Monochrome Indigo (Architectural)',
        'template': 'bright',
        'background': '#f8f9fb',
        'water_fill': '#b5c4d6',
        'water_outline': '#7a99be',
        'waterway_line': '#7a99be',
        'land_fill': '#f8f9fb',
        'wood_fill': '#e2e7ee',
        'park_fill': '#e2e7ee',
        'residential_fill': '#eef1f5',
        'commercial_fill': '#e6ebf2',
        'industrial_fill': '#dde3ed',
        'special_fill': '#e6ebf2',
        'sand_fill': '#f0f3f8',
        'glacier_fill': '#edf1f7',
        'building_fill': '#dcdee5',
        'building_outline': '#b8becd',
        'motorway_casing': '#0a1726',
        'motorway_fill': '#1a3352',
        'primary_casing': '#244163',
        'primary_fill': '#35567e',
        'secondary_casing': '#506f94',
        'secondary_fill': '#6b88ab',
        'minor_casing': '#91a8c3',
        'minor_fill': '#ffffff',
        'path_line': '#7b8fa7',
        'rail_line': '#24364c',
        'include_rail_ticks': True,
        'rail_ticks_color': '#ffffff',
        'boundary_country': '#1a2c42',
        'boundary_state': '#3d5675',
        'label_city': '#091624',
        'label_city_halo': '#f8f9fb',
        'label_country': '#1a2c42',
        'label_country_halo': '#f8f9fb',
        'label_water': '#315278',
        'label_water_halo': '#b5c4d6',
        'label_road': '#1a3352',
        'label_road_halo': '#ffffff'
    },

    'monochrome-sepia': {
        'name': 'Monochrome Sepia (Copperplate)',
        'template': 'bright',
        'background': '#faf7f0',
        'water_fill': '#d9cbb4',
        'water_outline': '#a89374',
        'waterway_line': '#a89374',
        'land_fill': '#faf7f0',
        'wood_fill': '#ede4d1',
        'park_fill': '#ede4d1',
        'residential_fill': '#f3ede0',
        'commercial_fill': '#ece4d4',
        'industrial_fill': '#e4d9c6',
        'special_fill': '#ece4d4',
        'sand_fill': '#f5ede0',
        'glacier_fill': '#f0ebd9',
        'building_fill': '#e8ddc8',
        'building_outline': '#c9bba3',
        'motorway_casing': '#211708',
        'motorway_fill': '#3d2b12',
        'primary_casing': '#4a3518',
        'primary_fill': '#6b4f26',
        'secondary_casing': '#826336',
        'secondary_fill': '#9e7d4c',
        'minor_casing': '#ba9f74',
        'minor_fill': '#ffffff',
        'path_line': '#94784e',
        'rail_line': '#3d2b12',
        'include_rail_ticks': True,
        'rail_ticks_color': '#faf7f0',
        'boundary_country': '#2e1e0a',
        'boundary_state': '#573d19',
        'label_city': '#1f1304',
        'label_city_halo': '#faf7f0',
        'label_country': '#33200a',
        'label_country_halo': '#faf7f0',
        'label_water': '#523c1e',
        'label_water_halo': '#d9cbb4',
        'label_road': '#33200a',
        'label_road_halo': '#ffffff'
    },

    'monochrome-emerald': {
        'name': 'Monochrome Emerald (Botanical)',
        'template': 'bright',
        'background': '#f4f8f5',
        'water_fill': '#b3d4bb',
        'water_outline': '#73a47e',
        'waterway_line': '#73a47e',
        'land_fill': '#f4f8f5',
        'wood_fill': '#dbeade',
        'park_fill': '#dbeade',
        'residential_fill': '#eaf2ec',
        'commercial_fill': '#e1ece3',
        'industrial_fill': '#d6e4d8',
        'special_fill': '#e1ece3',
        'sand_fill': '#eff5f0',
        'glacier_fill': '#e6f0e9',
        'building_fill': '#d5e4d8',
        'building_outline': '#b2cbb6',
        'motorway_casing': '#071a0c',
        'motorway_fill': '#11361b',
        'primary_casing': '#184523',
        'primary_fill': '#265e34',
        'secondary_casing': '#3b794b',
        'secondary_fill': '#529864',
        'minor_casing': '#7bb38a',
        'minor_fill': '#ffffff',
        'path_line': '#457d54',
        'rail_line': '#11361b',
        'include_rail_ticks': True,
        'rail_ticks_color': '#f4f8f5',
        'boundary_country': '#0f2915',
        'boundary_state': '#244f2e',
        'label_city': '#081a0e',
        'label_city_halo': '#f4f8f5',
        'label_country': '#11311a',
        'label_country_halo': '#f4f8f5',
        'label_water': '#1d4d2b',
        'label_water_halo': '#b3d4bb',
        'label_road': '#11361b',
        'label_road_halo': '#ffffff'
    },

    'monochrome-amber': {
        'name': 'Monochrome Amber (Warm Ochre)',
        'template': 'bright',
        'background': '#fdfaf2',
        'water_fill': '#e5d39e',
        'water_outline': '#ba9c4e',
        'waterway_line': '#ba9c4e',
        'land_fill': '#fdfaf2',
        'wood_fill': '#f4ebd2',
        'park_fill': '#f4ebd2',
        'residential_fill': '#f7f2e4',
        'commercial_fill': '#f0e9d6',
        'industrial_fill': '#e8dfc7',
        'special_fill': '#f0e9d6',
        'sand_fill': '#fbf6ea',
        'glacier_fill': '#f5eee0',
        'building_fill': '#ece0c1',
        'building_outline': '#cfbf95',
        'motorway_casing': '#241802',
        'motorway_fill': '#473005',
        'primary_casing': '#593d08',
        'primary_fill': '#7a550d',
        'secondary_casing': '#9c7017',
        'secondary_fill': '#bd8d28',
        'minor_casing': '#d1aa54',
        'minor_fill': '#ffffff',
        'path_line': '#8f6b1e',
        'rail_line': '#473005',
        'include_rail_ticks': True,
        'rail_ticks_color': '#fdfaf2',
        'boundary_country': '#382504',
        'boundary_state': '#66440b',
        'label_city': '#1f1401',
        'label_city_halo': '#fdfaf2',
        'label_country': '#3b2705',
        'label_country_halo': '#fdfaf2',
        'label_water': '#543b09',
        'label_water_halo': '#e5d39e',
        'label_road': '#3b2705',
        'label_road_halo': '#ffffff'
    },

    'monochrome-purple': {
        'name': 'Monochrome Purple (Amethyst Night)',
        'template': 'bright',
        'background': '#0c0514',
        'water_fill': '#1f0c38',
        'water_outline': '#a866fa',
        'waterway_line': '#ba7eff',
        'land_fill': '#0c0514',
        'wood_fill': '#180b2c',
        'park_fill': '#180b2c',
        'residential_fill': '#140824',
        'commercial_fill': '#190a2c',
        'industrial_fill': '#1e0d33',
        'special_fill': '#190a2c',
        'sand_fill': '#24113d',
        'glacier_fill': '#2a1445',
        'building_fill': '#2d134d',
        'building_outline': '#6d29b8',
        'motorway_casing': '#520d91',
        'motorway_fill': '#e0b5ff',
        'primary_casing': '#3e0773',
        'primary_fill': '#c780ff',
        'secondary_casing': '#2f045c',
        'secondary_fill': '#a352f5',
        'minor_casing': '#220542',
        'minor_fill': '#7b32c7',
        'path_line': '#994eed',
        'rail_line': '#dcb3ff',
        'include_rail_ticks': True,
        'rail_ticks_color': '#0c0514',
        'boundary_country': '#b875ff',
        'boundary_state': '#8230db',
        'label_city': '#ffffff',
        'label_city_halo': '#0c0514',
        'label_country': '#d6b0ff',
        'label_country_halo': '#0c0514',
        'label_water': '#c28aff',
        'label_water_halo': '#1f0c38',
        'label_road': '#f2e0ff',
        'label_road_halo': '#0c0514'
    },

    'monochrome-crimson': {
        'name': 'Monochrome Crimson (Oxblood Night)',
        'template': 'bright',
        'background': '#100305',
        'water_fill': '#2b060d',
        'water_outline': '#d92b51',
        'waterway_line': '#f03c64',
        'land_fill': '#100305',
        'wood_fill': '#1c0409',
        'park_fill': '#1c0409',
        'residential_fill': '#160307',
        'commercial_fill': '#1c0409',
        'industrial_fill': '#24060c',
        'special_fill': '#1c0409',
        'sand_fill': '#29070e',
        'glacier_fill': '#300a12',
        'building_fill': '#3b0914',
        'building_outline': '#82192e',
        'motorway_casing': '#6b0b1e',
        'motorway_fill': '#ff8ca6',
        'primary_casing': '#520616',
        'primary_fill': '#f54c73',
        'secondary_casing': '#3d030f',
        'secondary_fill': '#db3056',
        'minor_casing': '#2b030a',
        'minor_fill': '#a31d39',
        'path_line': '#c22d4f',
        'rail_line': '#ff7a99',
        'include_rail_ticks': True,
        'rail_ticks_color': '#100305',
        'boundary_country': '#eb446b',
        'boundary_state': '#ab1b3b',
        'label_city': '#ffffff',
        'label_city_halo': '#100305',
        'label_country': '#ffb0c2',
        'label_country_halo': '#100305',
        'label_water': '#f26383',
        'label_water_halo': '#2b060d',
        'label_road': '#ffe0e7',
        'label_road_halo': '#100305'
    },

    'monochrome-blue': {
        'name': 'Monochrome Soft Blue (Powder)',
        'template': 'bright',
        'background': '#f2f6fa',
        'water_fill': '#b4d4eb',
        'water_outline': '#5c9ac6',
        'waterway_line': '#5c9ac6',
        'land_fill': '#f2f6fa',
        'wood_fill': '#dbe8f2',
        'park_fill': '#dbe8f2',
        'residential_fill': '#eaf2f8',
        'commercial_fill': '#e1ecf5',
        'industrial_fill': '#d7e4ef',
        'special_fill': '#e1ecf5',
        'sand_fill': '#edf4fa',
        'glacier_fill': '#f0f5fa',
        'building_fill': '#cbdfe9',
        'building_outline': '#92b5cb',
        'motorway_casing': '#0a2336',
        'motorway_fill': '#15486e',
        'primary_casing': '#183d59',
        'primary_fill': '#245a82',
        'secondary_casing': '#32688f',
        'secondary_fill': '#4d8ebc',
        'minor_casing': '#89b8d9',
        'minor_fill': '#ffffff',
        'path_line': '#487fa8',
        'rail_line': '#10344d',
        'include_rail_ticks': True,
        'rail_ticks_color': '#f2f6fa',
        'boundary_country': '#11344f',
        'boundary_state': '#2d6085',
        'label_city': '#0a2030',
        'label_city_halo': '#f2f6fa',
        'label_country': '#153248',
        'label_country_halo': '#f2f6fa',
        'label_water': '#29618a',
        'label_water_halo': '#b4d4eb',
        'label_road': '#193a52',
        'label_road_halo': '#ffffff'
    },

    'monochrome-pink': {
        'name': 'Monochrome Soft Pink (Blush)',
        'template': 'bright',
        'background': '#fbf4f5',
        'water_fill': '#dbb3bb',
        'water_outline': '#b96475',
        'waterway_line': '#b96475',
        'land_fill': '#fbf4f5',
        'wood_fill': '#eddee1',
        'park_fill': '#eddee1',
        'residential_fill': '#f6eaec',
        'commercial_fill': '#f1e4e7',
        'industrial_fill': '#e8d9dc',
        'special_fill': '#f1e4e7',
        'sand_fill': '#f8edef',
        'glacier_fill': '#f9f0f2',
        'building_fill': '#e2cbcf',
        'building_outline': '#c99ca5',
        'motorway_casing': '#361119',
        'motorway_fill': '#662431',
        'primary_casing': '#4e1d27',
        'primary_fill': '#823545',
        'secondary_casing': '#71333f',
        'secondary_fill': '#ad5264',
        'minor_casing': '#c8939e',
        'minor_fill': '#ffffff',
        'path_line': '#9b4657',
        'rail_line': '#42151e',
        'include_rail_ticks': True,
        'rail_ticks_color': '#fbf4f5',
        'boundary_country': '#491822',
        'boundary_state': '#7b3241',
        'label_city': '#280b11',
        'label_city_halo': '#fbf4f5',
        'label_country': '#40171f',
        'label_country_halo': '#fbf4f5',
        'label_water': '#72313e',
        'label_water_halo': '#dbb3bb',
        'label_road': '#481922',
        'label_road_halo': '#ffffff'
    },

    'eighties-pastel': {
        'name': '1980s Pastel (Miami & Memphis)',
        'template': 'bright',
        'background': '#fef9f5',
        'water_fill': '#8fe1eb',
        'water_outline': '#40c0cb',
        'waterway_line': '#40c0cb',
        'land_fill': '#fef9f5',
        'wood_fill': '#b5efd3',
        'park_fill': '#b5efd3',
        'residential_fill': '#fcf0e8',
        'commercial_fill': '#fae3d9',
        'industrial_fill': '#f3d9ce',
        'special_fill': '#fae3d9',
        'sand_fill': '#fff3c4',
        'glacier_fill': '#f7effb',
        'building_fill': '#fce4ec',
        'building_outline': '#f48fb1',
        'motorway_casing': '#d81b60',
        'motorway_fill': '#ff4081',
        'primary_casing': '#0097a7',
        'primary_fill': '#00e5ff',
        'secondary_casing': '#fbc02d',
        'secondary_fill': '#ffee58',
        'minor_casing': '#dfd0cb',
        'minor_fill': '#ffffff',
        'path_line': '#26a69a',
        'rail_line': '#ab47bc',
        'include_rail_ticks': True,
        'rail_ticks_color': '#ffffff',
        'boundary_country': '#8e24aa',
        'boundary_state': '#ba68c8',
        'label_city': '#4a154b',
        'label_city_halo': '#ffffff',
        'label_country': '#6a1b9a',
        'label_country_halo': '#ffffff',
        'label_water': '#006064',
        'label_water_halo': '#e0f7fa',
        'label_road': '#37474f',
        'label_road_halo': '#ffffff'
    },

    'eighties-neon': {
        'name': '1980s Neon (Synthwave & Cyber)',
        'template': 'bright',
        'background': '#0d021a',
        'water_fill': '#16042b',
        'water_outline': '#00f0ff',
        'waterway_line': '#00f0ff',
        'land_fill': '#0d021a',
        'wood_fill': '#1a0533',
        'park_fill': '#1a0533',
        'residential_fill': '#120324',
        'commercial_fill': '#1a0533',
        'industrial_fill': '#140226',
        'special_fill': '#1a0533',
        'sand_fill': '#2b1442',
        'glacier_fill': '#1a0730',
        'building_fill': '#240a3d',
        'building_outline': '#ff007f',
        'motorway_casing': '#7a003f',
        'motorway_fill': '#ff007f',
        'primary_casing': '#005966',
        'primary_fill': '#00f0ff',
        'secondary_casing': '#596600',
        'secondary_fill': '#ffe600',
        'minor_casing': '#20083b',
        'minor_fill': '#551a8b',
        'path_line': '#ff00aa',
        'rail_line': '#39ff14',
        'include_rail_ticks': True,
        'rail_ticks_color': '#0d021a',
        'boundary_country': '#ff00ea',
        'boundary_state': '#bd00ff',
        'label_city': '#ffffff',
        'label_city_halo': '#0d021a',
        'label_country': '#ff99e6',
        'label_country_halo': '#0d021a',
        'label_water': '#00f0ff',
        'label_water_halo': '#16042b',
        'label_road': '#ffffff',
        'label_road_halo': '#0d021a'
    }
}

def generate_streetmap_minimal(dist_dir):
    """
    Generates the standalone lightweight Streetmap UK style
    based on the direct specification from the Gemini chat PDF.
    """
    style = {
        "version": 8,
        "name": "Streetmap UK Minimal",
        "glyphs": GLYPHS_URL,
        "sprite": SPRITE_URL,
        "sources": {
            "openmaptiles": {
                "type": "vector",
                "url": TILE_SOURCE_URL
            }
        },
        "layers": [
            {
                "id": "background",
                "type": "background",
                "paint": {
                    "background-color": "#fcfbf7"
                }
            },
            {
                "id": "landuse_park",
                "type": "fill",
                "source": "openmaptiles",
                "source-layer": "park",
                "paint": {
                    "fill-color": "#d9eec7",
                    "fill-opacity": 0.8
                }
            },
            {
                "id": "water",
                "type": "fill",
                "source": "openmaptiles",
                "source-layer": "water",
                "paint": {
                    "fill-color": "#9ed5ea",
                    "fill-outline-color": "#6eaec8"
                }
            },
            {
                "id": "building",
                "type": "fill",
                "source": "openmaptiles",
                "source-layer": "building",
                "paint": {
                    "fill-color": "#eae4db",
                    "fill-outline-color": "#cdc5b9"
                }
            },
            {
                "id": "tunnel_casing",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["==", "brunnel", "tunnel"],
                "paint": {
                    "line-color": "#a0a0a0",
                    "line-width": 4,
                    "line-dasharray": [2, 2]
                }
            },
            {
                "id": "road_residential_casing",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["all", ["==", "$type", "LineString"], ["in", "class", "minor", "service", "residential"]],
                "paint": {
                    "line-color": "#9e9e9e",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 12, 1.5, 16, 7]
                }
            },
            {
                "id": "road_residential_fill",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["all", ["==", "$type", "LineString"], ["in", "class", "minor", "service", "residential"]],
                "paint": {
                    "line-color": "#ffffff",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 12, 0.8, 16, 5]
                }
            },
            {
                "id": "road_secondary_casing",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["all", ["==", "$type", "LineString"], ["in", "class", "secondary", "tertiary"]],
                "paint": {
                    "line-color": "#8c4400",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 10, 2, 16, 9]
                }
            },
            {
                "id": "road_secondary_fill",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["all", ["==", "$type", "LineString"], ["in", "class", "secondary", "tertiary"]],
                "paint": {
                    "line-color": "#f59c1a",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 10, 1.2, 16, 7]
                }
            },
            {
                "id": "road_primary_casing",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["all", ["==", "$type", "LineString"], ["in", "class", "primary", "trunk"]],
                "paint": {
                    "line-color": "#004d25",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 8, 2, 16, 10]
                }
            },
            {
                "id": "road_primary_fill",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["all", ["==", "$type", "LineString"], ["in", "class", "primary", "trunk"]],
                "paint": {
                    "line-color": "#009a44",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 8, 1.2, 16, 8]
                }
            },
            {
                "id": "road_motorway_casing",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["all", ["==", "$type", "LineString"], ["==", "class", "motorway"]],
                "paint": {
                    "line-color": "#003b6d",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 6, 2.5, 16, 12]
                }
            },
            {
                "id": "road_motorway_fill",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["all", ["==", "$type", "LineString"], ["==", "class", "motorway"]],
                "paint": {
                    "line-color": "#0079c1",
                    "line-width": ["interpolate", ["linear"], ["zoom"], 6, 1.5, 16, 10]
                }
            },
            {
                "id": "railway_base",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["==", "class", "rail"],
                "paint": {
                    "line-color": "#444444",
                    "line-width": 2
                }
            },
            {
                "id": "railway_ticks",
                "type": "line",
                "source": "openmaptiles",
                "source-layer": "transportation",
                "filter": ["==", "class", "rail"],
                "paint": {
                    "line-color": "#ffffff",
                    "line-width": 1.5,
                    "line-dasharray": [1.5, 1.5]
                }
            },
            {
                "id": "ref_motorway_badge",
                "type": "symbol",
                "source": "openmaptiles",
                "source-layer": "transportation_name",
                "minzoom": 6,
                "filter": [
                    "all",
                    ["==", ["get", "class"], "motorway"],
                    ["has", "ref"]
                ],
                "layout": {
                    "icon-image": "shield_uk_motorway",
                    "icon-text-fit": "both",
                    "icon-text-fit-padding": [2, 5, 2, 5],
                    "icon-optional": True,
                    "text-field": ["to-string", ["get", "ref"]],
                    "text-font": FONT_MAP['bold'],
                    "text-size": 10,
                    "symbol-placement": "line",
                    "text-rotation-alignment": "viewport",
                    "icon-rotation-alignment": "viewport"
                },
                "paint": {
                    "text-color": "#ffffff"
                }
            },
            {
                "id": "ref_primary_a_road_badge",
                "type": "symbol",
                "source": "openmaptiles",
                "source-layer": "transportation_name",
                "minzoom": 7,
                "filter": [
                    "all",
                    ["match", ["get", "class"], ["primary", "trunk"], True, False],
                    ["has", "ref"]
                ],
                "layout": {
                    "icon-image": "shield_uk_primary",
                    "icon-text-fit": "both",
                    "icon-text-fit-padding": [2, 4, 2, 4],
                    "icon-optional": True,
                    "text-field": ["to-string", ["get", "ref"]],
                    "text-font": FONT_MAP['bold'],
                    "text-size": 10,
                    "symbol-placement": "line",
                    "text-rotation-alignment": "viewport",
                    "icon-rotation-alignment": "viewport"
                },
                "paint": {
                    "text-color": "#ffd200"
                }
            },
            {
                "id": "motorway_junction_badge",
                "type": "symbol",
                "source": "openmaptiles",
                "source-layer": "transportation_name",
                "minzoom": 10,
                "filter": [
                    "all",
                    [
                        "any",
                        ["==", ["get", "subclass"], "junction"],
                        ["==", ["get", "class"], "motorway_junction"]
                    ],
                    ["has", "ref"]
                ],
                "layout": {
                    "icon-image": "shield_uk_junction",
                    "icon-text-fit": "both",
                    "icon-text-fit-padding": [2, 4, 2, 4],
                    "icon-optional": True,
                    "text-field": ["to-string", ["get", "ref"]],
                    "text-font": FONT_MAP['bold'],
                    "text-size": 10,
                    "symbol-placement": "point",
                    "text-anchor": "center",
                    "text-rotation-alignment": "viewport",
                    "icon-rotation-alignment": "viewport",
                    "icon-allow-overlap": False,
                    "text-allow-overlap": False
                },
                "paint": {
                    "text-color": "#ffffff",
                    "text-halo-color": "#111111",
                    "text-halo-width": 2
                }
            },
            {
                "id": "road_label",
                "type": "symbol",
                "source": "openmaptiles",
                "source-layer": "transportation_name",
                "layout": {
                    "symbol-placement": "line",
                    "text-field": "{name}",
                    "text-font": FONT_MAP['regular'],
                    "text-size": 11,
                    "text-letter-spacing": 0.05
                },
                "paint": {
                    "text-color": "#1b1b1b",
                    "text-halo-color": "#ffffff",
                    "text-halo-width": 1.5
                }
            },
            {
                "id": "place_label_town",
                "type": "symbol",
                "source": "openmaptiles",
                "source-layer": "place",
                "filter": ["match", ["get", "class"], ["town", "city"], True, False],
                "layout": {
                    "text-field": "{name}",
                    "text-font": FONT_MAP['bold'],
                    "text-size": ["interpolate", ["linear"], ["zoom"], 8, 12, 14, 18],
                    "text-transform": "uppercase"
                },
                "paint": {
                    "text-color": "#222222",
                    "text-halo-color": "#ffffff",
                    "text-halo-width": 2
                }
            }
        ]
    }
    out_f = os.path.join(dist_dir, "streetmap-minimal.json")
    with open(out_f, 'w') as f:
        json.dump(style, f, indent=2)
    return "streetmap-minimal.json"

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_dir = os.path.join(root, 'reference-styles')
    dist_dir = os.path.join(root, 'dist')
    os.makedirs(dist_dir, exist_ok=True)

    # Clean old JSON files in dist/
    for old_f in os.listdir(dist_dir):
        if old_f.endswith('.json'):
            os.remove(os.path.join(dist_dir, old_f))

    with open(os.path.join(ref_dir, 'bright.json'), 'r') as f:
        bright_template = json.load(f)

    generated = []

    # 1. Canvas Styles (Both Unified and Split Base / Ref)
    for c_id in ['light-gray', 'dark-gray']:
        theme = THEMES[c_id]
        
        # Unified
        style_unified = compile_style(bright_template, theme)
        out_f = os.path.join(dist_dir, f"{c_id}.json")
        with open(out_f, 'w') as f:
            json.dump(style_unified, f, indent=2)
        generated.append(f"{c_id}.json")

        # Base only
        base_theme = copy.deepcopy(theme)
        base_theme['name'] = f"{theme['name']} (Base)"
        style_base = compile_style(bright_template, base_theme, is_base_only=True)
        out_f = os.path.join(dist_dir, f"{c_id}-base.json")
        with open(out_f, 'w') as f:
            json.dump(style_base, f, indent=2)
        generated.append(f"{c_id}-base.json")

        # Ref only
        ref_theme = copy.deepcopy(theme)
        ref_theme['name'] = f"{theme['name']} (Reference)"
        style_ref = compile_style(bright_template, ref_theme, is_ref_only=True)
        out_f = os.path.join(dist_dir, f"{c_id}-ref.json")
        with open(out_f, 'w') as f:
            json.dump(style_ref, f, indent=2)
        generated.append(f"{c_id}-ref.json")

    # 2. General Basemaps (Navigation, Streets, OSM)
    for theme_id in ['navigation', 'navigation-dark', 'streets', 'streets-night', 'osm']:
        theme = THEMES[theme_id]
        style = compile_style(bright_template, theme)
        out_f = os.path.join(dist_dir, f"{theme_id}.json")
        with open(out_f, 'w') as f:
            json.dump(style, f, indent=2)
        generated.append(f"{theme_id}.json")

    # 3. Topographic and Relief Basemaps
    topo_theme = THEMES['topographic']
    topo_style = compile_style(bright_template, topo_theme, include_relief=True)
    with open(os.path.join(dist_dir, 'topographic.json'), 'w') as f:
        json.dump(topo_style, f, indent=2)
    generated.append('topographic.json')

    # 4. Ordnance Survey & British Cartography (Roads, Streetmap UK, Outdoor, Light)
    for os_id in ['os-roads', 'streetmap', 'os-outdoor', 'os-light']:
        os_theme = THEMES[os_id]
        include_rel = os_theme.get('include_relief', False)
        os_style = compile_style(bright_template, os_theme, include_relief=include_rel)
        out_f = os.path.join(dist_dir, f"{os_id}.json")
        with open(out_f, 'w') as f:
            json.dump(os_style, f, indent=2)
        generated.append(f"{os_id}.json")

    # Standalone minimal Streetmap UK style
    min_f = generate_streetmap_minimal(dist_dir)
    generated.append(min_f)

    # 5. Creative Basemaps (Modern Antique, Newspaper, Nova, Colored Pencil, Charted Territory, Midcentury, Blueprint)
    for cr_id in ['modern-antique', 'newspaper', 'nova', 'colored-pencil', 'charted-territory', 'midcentury', 'blueprint']:
        cr_theme = THEMES[cr_id]
        include_rel = cr_theme.get('include_relief', False)
        cr_style = compile_style(bright_template, cr_theme, include_relief=include_rel)
        out_f = os.path.join(dist_dir, f"{cr_id}.json")
        with open(out_f, 'w') as f:
            json.dump(cr_style, f, indent=2)
        generated.append(f"{cr_id}.json")

    # 6. Human Geography Series (Light & Dark, with Base variants)
    for hg_id in ['human-geography', 'human-geography-dark']:
        hg_theme = THEMES[hg_id]
        # Unified
        hg_style = compile_style(bright_template, hg_theme)
        out_f = os.path.join(dist_dir, f"{hg_id}.json")
        with open(out_f, 'w') as f:
            json.dump(hg_style, f, indent=2)
        generated.append(f"{hg_id}.json")

        # Base only
        hg_base_theme = copy.deepcopy(hg_theme)
        hg_base_theme['name'] = f"{hg_theme['name']} (Base)"
        hg_base_style = compile_style(bright_template, hg_base_theme, is_base_only=True)
        out_f = os.path.join(dist_dir, f"{hg_id}-base.json")
        with open(out_f, 'w') as f:
            json.dump(hg_base_style, f, indent=2)
        generated.append(f"{hg_id}-base.json")

    # 7. Additional Topography, Community, Marine & Outdoor
    for ad_id in ['community', 'outdoor', 'terrain', 'oceans']:
        ad_theme = THEMES[ad_id]
        include_rel = ad_theme.get('include_relief', False)
        ad_style = compile_style(bright_template, ad_theme, include_relief=include_rel)
        out_f = os.path.join(dist_dir, f"{ad_id}.json")
        with open(out_f, 'w') as f:
            json.dump(ad_style, f, indent=2)
        generated.append(f"{ad_id}.json")

    # 8. Consumer Maps Pack (Google Maps Modern/Warm/Pastel/Retro, MapQuest, HERE, Apple, Bing)
    for cs_id in ['google-maps-modern', 'google-maps', 'google-maps-2009', 'google-maps-retro', 'mapquest-classic', 'here-classic', 'apple-maps', 'bing-maps']:
        cs_theme = THEMES[cs_id]
        cs_style = compile_style(bright_template, cs_theme)
        out_f = os.path.join(dist_dir, f"{cs_id}.json")
        with open(out_f, 'w') as f:
            json.dump(cs_style, f, indent=2)
        generated.append(f"{cs_id}.json")

    # 9. Motoring & Road Atlases (Michelin, AA Atlas, Rand McNally, OS Landranger, Swisstopo)
    for mr_id in ['michelin', 'aa-atlas', 'rand-mcnally', 'os-landranger', 'swisstopo']:
        mr_theme = THEMES[mr_id]
        include_rel = mr_theme.get('include_relief', False)
        mr_style = compile_style(bright_template, mr_theme, include_relief=include_rel)
        out_f = os.path.join(dist_dir, f"{mr_id}.json")
        with open(out_f, 'w') as f:
            json.dump(mr_style, f, indent=2)
        generated.append(f"{mr_id}.json")

    # 10. Web-Map Classics & Wildcards (Stamen Toner, CARTO Voyager, NatGeo)
    for cw_id in ['stamen-toner', 'carto-voyager', 'natgeo']:
        cw_theme = THEMES[cw_id]
        include_rel = cw_theme.get('include_relief', False)
        cw_style = compile_style(bright_template, cw_theme, include_relief=include_rel)
        out_f = os.path.join(dist_dir, f"{cw_id}.json")
        with open(out_f, 'w') as f:
            json.dump(cw_style, f, indent=2)
        generated.append(f"{cw_id}.json")

    # 11. Ordnance Survey Accessible & Night (Night, Deuteranopia, Tritanopia)
    for os_acc_id in ['os-zoomstack-night', 'os-deuteranopia', 'os-tritanopia']:
        os_acc_theme = THEMES[os_acc_id]
        os_acc_style = compile_style(bright_template, os_acc_theme)
        out_f = os.path.join(dist_dir, f"{os_acc_id}.json")
        with open(out_f, 'w') as f:
            json.dump(os_acc_style, f, indent=2)
        generated.append(f"{os_acc_id}.json")

    # 12. OSM Ecosystem & Transit (OSM Carto, Humanitarian HOT, Thunderforest Transport)
    for osm_id in ['osm-carto', 'humanitarian', 'transport-transit']:
        osm_theme = THEMES[osm_id]
        osm_style = compile_style(bright_template, osm_theme)
        out_f = os.path.join(dist_dir, f"{osm_id}.json")
        with open(out_f, 'w') as f:
            json.dump(osm_style, f, indent=2)
        generated.append(f"{osm_id}.json")

    # 13. Monochrome Single-Hue Series (Indigo, Sepia, Emerald, Amber, Purple, Crimson, Pink, Blue)
    for mono_id in ['monochrome-indigo', 'monochrome-sepia', 'monochrome-emerald', 'monochrome-amber', 'monochrome-purple', 'monochrome-crimson', 'monochrome-pink', 'monochrome-blue']:
        mono_theme = THEMES[mono_id]
        mono_style = compile_style(bright_template, mono_theme)
        out_f = os.path.join(dist_dir, f"{mono_id}.json")
        with open(out_f, 'w') as f:
            json.dump(mono_style, f, indent=2)
        generated.append(f"{mono_id}.json")

    # 14. 1980s Retro Aesthetics (Pastel & Neon)
    for eighties_id in ['eighties-pastel', 'eighties-neon']:
        eighties_theme = THEMES[eighties_id]
        eighties_style = compile_style(bright_template, eighties_theme)
        out_f = os.path.join(dist_dir, f"{eighties_id}.json")
        with open(out_f, 'w') as f:
            json.dump(eighties_style, f, indent=2)
        generated.append(f"{eighties_id}.json")

    # 15. OpenFreeMap Core Reference Styles (Part 2)
    ref_map = {
        'liberty': 'OpenFreeMap Liberty',
        'bright': 'OpenFreeMap Bright',
        'positron': 'OpenFreeMap Positron',
        'fiord': 'OpenFreeMap Fiord',
        'dark': 'OpenFreeMap Dark'
    }
    for ref_id, ref_name in ref_map.items():
        ref_path = os.path.join(ref_dir, f"{ref_id}.json")
        if os.path.exists(ref_path):
            with open(ref_path, 'r', encoding='utf-8') as f:
                ref_json = json.load(f)
            ref_json['name'] = ref_name
            out_f = os.path.join(dist_dir, f"{ref_id}.json")
            with open(out_f, 'w', encoding='utf-8') as f:
                json.dump(ref_json, f, indent=2)
            generated.append(f"{ref_id}.json")

    def get_style_display_name(fname):
        base_id = fname.replace('.json', '')
        if base_id in ref_map:
            return ref_map[base_id]
        if fname == 'streetmap-minimal.json':
            return 'Streetmap UK (Minimal)'
        clean_id = base_id.replace('-base', '').replace('-ref', '')
        t_name = THEMES.get(clean_id, {}).get('name', base_id)
        if fname.endswith('-base.json'):
            return f"{t_name} (Base)"
        if fname.endswith('-ref.json'):
            return f"{t_name} (Reference)"
        return t_name

    # Create index manifest for distribution
    manifest = {
        'generator': 'compile_styles.py',
        'source_tile_provider': 'OpenFreeMap (https://openfreemap.org/)',
        'tile_schema': 'OpenMapTiles v3.x',
        'styles': [
            {
                'id': fname.replace('.json', ''),
                'file': fname,
                'path': f"dist/{fname}",
                'name': get_style_display_name(fname)
            }
            for fname in generated
        ]
    }
    with open(os.path.join(dist_dir, 'styles-index.json'), 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"Successfully compiled {len(generated)} MapLibre styles to dist/:")
    for g in generated:
        print(f"  ✓ dist/{g}")

    # Mirror to docs/dist/ for standalone docs/GitHub Pages hosting
    docs_dist = os.path.join(root, 'docs', 'dist')
    os.makedirs(docs_dist, exist_ok=True)
    import shutil
    for fname in os.listdir(dist_dir):
        if fname.endswith('.json'):
            shutil.copy2(os.path.join(dist_dir, fname), os.path.join(docs_dist, fname))
    print(f"  ✓ Mirrored styles to docs/dist/ for GitHub Pages compatibility.")

if __name__ == '__main__':
    main()

