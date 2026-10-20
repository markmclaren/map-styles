#!/usr/bin/env python3
"""
Download and archive all 11 ArcGIS vector basemap styles locally.
Reads URLs from README.md, queries metadata, and saves JSONs to source-styles/.
"""

import os
import re
import json
import urllib.request

STYLE_NAMES = {
    '291da5eab3a0412593b66d384379f89f': 'light-gray-canvas-base',
    '1768e8369a214dfab4e2167d5c5f2454': 'light-gray-canvas-ref',
    '5e9b3685f4c24d8781073dd928ebda50': 'dark-gray-canvas-base',
    '747cb7a5329c478cbe6981076cc879c5': 'dark-gray-canvas-ref',
    '63c47b7177f946b49902c24129b87252': 'world-navigation',
    'b69e76a446ac479998ff31de839ba323': 'world-navigation-dark',
    'de26a3cf4cc9451298ea173c4b324736': 'world-street-map',
    '86f556a2d1fd468181855a35e344567f': 'world-street-map-night',
    'b266e6d17fc345b498345613930fbd76': 'world-street-map-relief',
    '7dc6cea0b1764a1f9af2e679f642f0f5': 'world-topographic',
    '3e1a00aeae81496587988075fe529f71': 'openstreetmap-esri',
}

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readme_path = os.path.join(root_dir, 'README.md')
    out_dir = os.path.join(root_dir, 'source-styles')
    os.makedirs(out_dir, exist_ok=True)

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = [line.strip() for line in content.splitlines() if line.strip().startswith('https://www.arcgis.com/')]
    unique_urls = list(dict.fromkeys(lines))

    manifest = {}

    print(f"Found {len(unique_urls)} unique ArcGIS style URLs.")
    for url in unique_urls:
        match = re.search(r'/items/([a-f0-9]{32})/', url)
        if not match:
            continue
        item_id = match.group(1)
        name = STYLE_NAMES.get(item_id, f"item-{item_id}")
        out_file = os.path.join(out_dir, f"{name}.json")

        print(f"Downloading [{item_id}] -> {name}.json ...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            
            with open(out_file, 'w', encoding='utf-8') as out_f:
                json.dump(data, out_f, indent=2)

            layer_count = len(data.get('layers', []))
            manifest[name] = {
                'item_id': item_id,
                'file': f"source-styles/{name}.json",
                'layers': layer_count,
                'version': data.get('version'),
                'sprite': data.get('sprite'),
                'glyphs': data.get('glyphs')
            }
            print(f"  ✓ Saved {name}.json ({layer_count} layers)")
        except Exception as e:
            print(f"  ✗ Failed {item_id}: {e}")

    manifest_file = os.path.join(out_dir, 'manifest.json')
    with open(manifest_file, 'w', encoding='utf-8') as mf:
        json.dump(manifest, mf, indent=2)
    print(f"\nSaved manifest to source-styles/manifest.json")

if __name__ == '__main__':
    main()
