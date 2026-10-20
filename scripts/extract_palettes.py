#!/usr/bin/env python3
"""
Extract comprehensive color palettes and styling properties from all ArcGIS source styles.
Outputs structured JSON palettes into palettes/.
"""

import os
import json
from collections import defaultdict

def extract_color_stops(prop):
    """Normalize color stops or return single color."""
    if isinstance(prop, str):
        return prop
    if isinstance(prop, dict) and 'stops' in prop:
        return prop['stops']
    if isinstance(prop, dict) and 'base' in prop and 'stops' in prop:
        return prop['stops']
    return prop

def analyze_style(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    palette = {
        'id': os.path.basename(file_path).replace('.json', ''),
        'version': data.get('version'),
        'background': '#ffffff',
        'water': {},
        'waterway': {},
        'land': {},
        'greenery': {},
        'urban': {},
        'building': {},
        'roads': {},
        'boundaries': {},
        'labels': {}
    }

    layers = data.get('layers', [])

    for layer in layers:
        l_id = layer.get('id', '')
        l_type = layer.get('type')
        s_layer = layer.get('source-layer', '')
        paint = layer.get('paint', {})
        layout = layer.get('layout', {})

        # Background
        if l_type == 'background':
            bg = paint.get('background-color')
            if bg:
                palette['background'] = extract_color_stops(bg)

        # Water
        if 'water' in s_layer.lower() or 'marine' in s_layer.lower() or 'bathymetry' in s_layer.lower():
            if l_type == 'fill':
                c = paint.get('fill-color')
                if c and 'fill' not in palette['water']:
                    palette['water']['fill'] = extract_color_stops(c)
                out = paint.get('fill-outline-color')
                if out and 'outline' not in palette['water']:
                    palette['water']['outline'] = extract_color_stops(out)
            elif l_type == 'line':
                c = paint.get('line-color')
                if c and 'line' not in palette['waterway']:
                    palette['waterway']['line'] = extract_color_stops(c)

        # Land
        if s_layer == 'Land' and l_type == 'fill':
            c = paint.get('fill-color')
            if c:
                palette['land']['base'] = extract_color_stops(c)

        # Greenery (Forest / Park)
        if any(w in s_layer.lower() or w in l_id.lower() for w in ['forest', 'park', 'wood', 'grass', 'openspace']):
            if l_type == 'fill':
                c = paint.get('fill-color')
                if c:
                    if 'park' in s_layer.lower() or 'park' in l_id.lower():
                        if 'park' not in palette['greenery']:
                            palette['greenery']['park'] = extract_color_stops(c)
                    else:
                        if 'wood' not in palette['greenery']:
                            palette['greenery']['wood'] = extract_color_stops(c)

        # Urban & Landuse
        if any(w in s_layer.lower() or w in l_id.lower() for w in ['urban', 'residential', 'commercial', 'industrial', 'cemetery', 'education', 'hospital']):
            if l_type == 'fill':
                c = paint.get('fill-color')
                if c:
                    key = 'residential'
                    if 'commercial' in l_id.lower() or 'retail' in l_id.lower():
                        key = 'commercial'
                    elif 'industrial' in l_id.lower():
                        key = 'industrial'
                    elif 'cemetery' in l_id.lower():
                        key = 'cemetery'
                    elif 'education' in l_id.lower():
                        key = 'school'
                    elif 'hospital' in l_id.lower() or 'medical' in l_id.lower():
                        key = 'hospital'
                    elif 'urban' in l_id.lower() or 'urban' in s_layer.lower():
                        key = 'urban_area'
                    
                    if key not in palette['urban']:
                        palette['urban'][key] = extract_color_stops(c)

        # Building
        if 'building' in s_layer.lower() or 'building' in l_id.lower():
            if l_type == 'fill':
                c = paint.get('fill-color')
                if c and 'fill' not in palette['building']:
                    palette['building']['fill'] = extract_color_stops(c)
                out = paint.get('fill-outline-color')
                if out and 'outline' not in palette['building']:
                    palette['building']['outline'] = extract_color_stops(out)

        # Roads
        if 'road' in s_layer.lower() or 'traffic' in l_id.lower():
            if l_type == 'line':
                c = paint.get('line-color')
                w = paint.get('line-width')
                is_casing = '/1' in l_id or 'casing' in l_id.lower()
                category = 'minor'
                if any(m in l_id.lower() for m in ['freeway', 'motorway']):
                    category = 'motorway'
                elif any(m in l_id.lower() for m in ['highway', 'major', 'trunk', 'primary']):
                    category = 'primary'
                elif any(m in l_id.lower() for m in ['secondary']):
                    category = 'secondary'
                elif any(m in l_id.lower() for m in ['service', 'track', '4wd']):
                    category = 'service'
                elif any(m in l_id.lower() for m in ['pedestrian', 'path', 'trail', 'cycleway']):
                    category = 'path'

                sub = 'casing' if is_casing else 'fill'
                if category not in palette['roads']:
                    palette['roads'][category] = {}
                if sub not in palette['roads'][category] and c:
                    palette['roads'][category][sub] = extract_color_stops(c)
                if f"{sub}_width" not in palette['roads'][category] and w:
                    palette['roads'][category][f"{sub}_width"] = w

        # Boundaries
        if 'boundary' in s_layer.lower() or 'admin' in l_id.lower() and l_type == 'line':
            c = paint.get('line-color')
            if c:
                if 'admin0' in l_id.lower() and 'country' not in palette['boundaries']:
                    palette['boundaries']['country'] = extract_color_stops(c)
                elif 'admin1' in l_id.lower() and 'state' not in palette['boundaries']:
                    palette['boundaries']['state'] = extract_color_stops(c)

        # Labels
        if l_type == 'symbol':
            tc = paint.get('text-color')
            hc = paint.get('text-halo-color')
            hw = paint.get('text-halo-width')
            if tc:
                target = 'general'
                if any(w in l_id.lower() for w in ['city', 'town', 'place']):
                    target = 'city'
                elif 'admin0' in l_id.lower() or 'country' in l_id.lower():
                    target = 'country'
                elif 'admin1' in l_id.lower() or 'state' in l_id.lower():
                    target = 'state'
                elif 'water' in l_id.lower():
                    target = 'water'
                elif 'road' in l_id.lower():
                    target = 'road'

                if target not in palette['labels']:
                    palette['labels'][target] = {
                        'text_color': extract_color_stops(tc),
                        'halo_color': extract_color_stops(hc) if hc else None,
                        'halo_width': hw
                    }

    return palette

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(root, 'source-styles')
    out_dir = os.path.join(root, 'palettes')
    os.makedirs(out_dir, exist_ok=True)

    for fname in sorted(os.listdir(src_dir)):
        if not fname.endswith('.json') or fname == 'manifest.json':
            continue
        fpath = os.path.join(src_dir, fname)
        p = analyze_style(fpath)
        out_path = os.path.join(out_dir, fname)
        with open(out_path, 'w', encoding='utf-8') as out_f:
            json.dump(p, out_f, indent=2)
        print(f"Extracted palette: {fname} -> palettes/{fname}")

if __name__ == '__main__':
    main()
