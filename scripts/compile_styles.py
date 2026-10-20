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

        # Apply Water
        elif s_layer == 'water' or 'water' in l_id:
            if l_type == 'fill':
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
                            0, 0.5,
                            6, 0.8,
                            12, 1.2
                        ]
                    }
                })
            continue
        elif s_layer == 'waterway':
            if l_type == 'line':
                paint['line-color'] = theme_config.get('waterway_line', theme_config.get('water_fill', '#a7d6fe'))

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
                elif 'glacier' in l_id or 'ice' in l_id:
                    paint['fill-color'] = '#ffffff'
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

        # Apply Boundaries
        elif s_layer == 'boundary':
            if l_type == 'line':
                if 'country' in l_id or 'admin_level_2' in l_id or 'admin-2' in l_id:
                    paint['line-color'] = theme_config.get('boundary_country', '#9c9c9c')
                else:
                    paint['line-color'] = theme_config.get('boundary_state', '#b9b9b9')

        # Apply Labels (Symbols)
        elif l_type == 'symbol':
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
            elif s_layer == 'water_name':
                paint['text-color'] = theme_config.get('label_water', '#436fb3')
                if 'label_water_halo' in theme_config:
                    paint['text-halo-color'] = theme_config['label_water_halo']
                    paint['text-halo-width'] = 1
            elif s_layer == 'transportation_name':
                paint['text-color'] = theme_config.get('label_road', '#666666')
                if 'label_road_halo' in theme_config:
                    paint['text-halo-color'] = theme_config['label_road_halo']
                    paint['text-halo-width'] = 1

        new_layers.append(layer)

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
        'background': '#323333',
        'water_fill': '#1d2224',
        'water_outline': '#141719',
        'waterway_line': '#141719',
        'land_fill': {'stops': [[0, '#3b3c3c'], [12, '#353636'], [15, '#323333']]},
        'wood_fill': {'stops': [[7, '#373837'], [9, '#373938']]},
        'park_fill': {'stops': [[7, '#373837'], [9, '#373938']]},
        'residential_fill': '#292b2c',
        'commercial_fill': '#2c2e2f',
        'industrial_fill': '#262829',
        'special_fill': '#2e2f2f',
        'sand_fill': '#383632',
        'building_fill': '#2e2f2f',
        'building_outline': '#232525',
        'motorway_casing': '#434749',
        'motorway_fill': '#585e61',
        'primary_casing': '#3b3f41',
        'primary_fill': '#4d5255',
        'secondary_casing': '#353839',
        'secondary_fill': '#44484b',
        'minor_casing': '#2e3032',
        'minor_fill': '#383a3c',
        'path_line': '#3d4042',
        'rail_line': '#2d2f30',
        'boundary_country': '#5c6063',
        'boundary_state': '#45484a',
        'label_city': '#b1b2ad',
        'label_city_halo': '#232729',
        'label_country': '#787a7b',
        'label_country_halo': '#1d2224',
        'label_water': '#626d70',
        'label_water_halo': '#1d2224',
        'label_road': '#707476',
        'label_road_halo': '#1d2224'
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
        'background': '#2f2e2c',
        'water_fill': '#3a4364',
        'water_outline': '#262d47',
        'waterway_line': '#262d47',
        'land_fill': '#2f2e2c',
        'wood_fill': '#2d382a',
        'park_fill': '#273324',
        'residential_fill': '#252422',
        'commercial_fill': '#2a2825',
        'industrial_fill': '#262523',
        'special_fill': '#282725',
        'sand_fill': '#3d3830',
        'building_fill': '#646464',
        'building_outline': '#444444',
        'motorway_casing': '#4a3319',
        'motorway_fill': '#cf8832',
        'primary_casing': '#453818',
        'primary_fill': '#ba9e38',
        'secondary_casing': '#3a3a3a',
        'secondary_fill': '#4c4c4c',
        'minor_casing': '#2c2c2c',
        'minor_fill': '#3d3d3d',
        'path_line': '#444444',
        'rail_line': '#555555',
        'boundary_country': '#706c8a',
        'boundary_state': '#55526b',
        'label_city': '#e0e0e0',
        'label_city_halo': '#1f2024',
        'label_country': '#98c295',
        'label_country_halo': '#1f2024',
        'label_water': '#8ba4d9',
        'label_water_halo': '#1f2024',
        'label_road': '#b0b0b0',
        'label_road_halo': '#1f2024'
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
        'background': '#222428',
        'water_fill': '#000F1A',
        'water_outline': '#092136',
        'waterway_line': '#092136',
        'land_fill': '#222428',
        'wood_fill': '#253328',
        'park_fill': '#253328',
        'residential_fill': '#26282d',
        'commercial_fill': '#292b30',
        'industrial_fill': '#242528',
        'special_fill': '#25262a',
        'sand_fill': '#302d28',
        'building_fill': '#36383e',
        'building_outline': '#2a2b30',
        'motorway_casing': '#4a2c10',
        'motorway_fill': '#a66624',
        'primary_casing': '#403310',
        'primary_fill': '#997e2f',
        'secondary_casing': '#2c2e33',
        'secondary_fill': '#44464c',
        'minor_casing': '#222326',
        'minor_fill': '#33353b',
        'path_line': '#383a40',
        'rail_line': '#444444',
        'boundary_country': '#544c66',
        'boundary_state': '#403a4d',
        'label_city': '#dcdde0',
        'label_city_halo': '#141517',
        'label_country': '#a295bd',
        'label_country_halo': '#141517',
        'label_water': '#4275a3',
        'label_water_halo': '#000F1A',
        'label_road': '#a0a2a8',
        'label_road_halo': '#141517'
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
    }
}

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

    # 4. Ordnance Survey Skins (Roads, Outdoor, Light)
    for os_id in ['os-roads', 'os-outdoor', 'os-light']:
        os_theme = THEMES[os_id]
        include_rel = os_theme.get('include_relief', False)
        os_style = compile_style(bright_template, os_theme, include_relief=include_rel)
        out_f = os.path.join(dist_dir, f"{os_id}.json")
        with open(out_f, 'w') as f:
            json.dump(os_style, f, indent=2)
        generated.append(f"{os_id}.json")

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
                'name': THEMES.get(fname.replace('.json', '').replace('-base', '').replace('-ref', '').replace('-relief', ''), {}).get('name', fname)
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

