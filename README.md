# Open Vector Map Styles for MapLibre GL (OpenFreeMap)

A collection of open-source vector map styles for **MapLibre GL** powered by free, open vector map tiles from **[OpenFreeMap](https://openfreemap.org/)** (based on the OpenMapTiles schema).

These styles provide a rich range of cartographic themes—including Ordnance Survey skins, neutral light/dark data canvas backdrops, high-contrast navigation maps, creative aesthetics (parchment, newspaper, cyberpunk nova, colored pencil, blueprint), and relief/topographic views.

---

## 🎨 Available Basemap Styles (`dist/`)

All compiled MapLibre style JSON files are located in [`dist/`](dist/) and are ready to load into MapLibre GL JS, MapLibre Native, Leaflet, OpenLayers, or QGIS without requiring an API key or token:

| Style File | Cartographic Theme | Description |
|---|---|---|
| [`dist/os-roads.json`](dist/os-roads.json) | **Ordnance Survey - Roads** | Iconic OS UK road network cartography (peach buildings, cyan motorways, green A-roads) |
| [`dist/os-outdoor.json`](dist/os-outdoor.json) | **Ordnance Survey - Outdoor** | Classic OS Landranger/Explorer outdoor styling with greenspaces & relief |
| [`dist/os-light.json`](dist/os-light.json) | **Ordnance Survey - Light** | Minimalist low-contrast backdrop designed for GIS data overlay |
| [`dist/modern-antique.json`](dist/modern-antique.json) | **Modern Antique** | Vintage antique parchment map with sepia tones & antique calligraphy feel |
| [`dist/newspaper.json`](dist/newspaper.json) | **Newspaper** | High-contrast editorial black & white / grayscale newspaper print aesthetic |
| [`dist/nova.json`](dist/nova.json) | **Nova** | Cyberpunk dark theme with deep obsidian blue & electric glowing cyan roads |
| [`dist/colored-pencil.json`](dist/colored-pencil.json) | **Colored Pencil** | Whimsical hand-drawn colored pencil & pastel sketch aesthetic |
| [`dist/charted-territory.json`](dist/charted-territory.json) | **Charted Territory** | Vintage exploration atlas map with warm olive greens, tan earth & relief |
| [`dist/midcentury.json`](dist/midcentury.json) | **Midcentury** | 1950s/1960s retro art style featuring turquoise waters, coral highways & mustard accents |
| [`dist/blueprint.json`](dist/blueprint.json) | **Blueprint** | Architectural drafting blueprint styling with deep blueprint blue & white lines |
| [`dist/human-geography.json`](dist/human-geography.json) | **Human Geography** | Ultra-clean neutral light monochrome backdrop designed for thematic overlays |
| [`dist/human-geography-base.json`](dist/human-geography-base.json) | **Human Geography (Base)** | Base layer without labels for sandwiching thematic data layers |
| [`dist/human-geography-dark.json`](dist/human-geography-dark.json) | **Human Geography Dark** | Dark slate/charcoal companion engineered for high-contrast thematic data |
| [`dist/human-geography-dark-base.json`](dist/human-geography-dark-base.json) | **Human Geography Dark (Base)**| Dark base layer without labels for thematic sandwiching |
| [`dist/community.json`](dist/community.json) | **Community** | Vibrant municipal cartography highlighting civic parks, paths & campuses |
| [`dist/outdoor.json`](dist/outdoor.json) | **Outdoor** | Recreation map with hiking trails, bike paths, parks & shaded relief |
| [`dist/terrain.json`](dist/terrain.json) | **Terrain** | Physical geography focused on elevation tinting, mountains & relief |
| [`dist/oceans.json`](dist/oceans.json) | **Oceans** | Marine cartography highlighting coastal contours & oceanic features |
| [`dist/light-gray.json`](dist/light-gray.json) | **Light Gray Canvas (Unified)** | Muted minimalist background with integrated labels |
| [`dist/light-gray-base.json`](dist/light-gray-base.json) | **Light Gray Canvas (Base)** | Base polygons & lines only (ideal for sandwiching thematic data) |
| [`dist/light-gray-ref.json`](dist/light-gray-ref.json) | **Light Gray Canvas (Reference)** | Overlay labels & boundaries with transparent background |
| [`dist/dark-gray.json`](dist/dark-gray.json) | **Dark Gray Canvas (Unified)** | Dark charcoal neutral theme with integrated labels |
| [`dist/dark-gray-base.json`](dist/dark-gray-base.json) | **Dark Gray Canvas (Base)** | Dark base polygons & lines only |
| [`dist/dark-gray-ref.json`](dist/dark-gray-ref.json) | **Dark Gray Canvas (Reference)** | Dark overlay labels & boundaries |
| [`dist/navigation.json`](dist/navigation.json) | **Navigation** | High-contrast daytime navigation cartography |
| [`dist/navigation-dark.json`](dist/navigation-dark.json) | **Navigation (Dark)** | Low-glare night navigation cartography |
| [`dist/streets.json`](dist/streets.json) | **Streets** | Classic street map styling |
| [`dist/streets-night.json`](dist/streets-night.json) | **Streets (Night)** | Low-light night street cartography |
| [`dist/topographic.json`](dist/topographic.json) | **Topographic** | Traditional contour/relief topographic look |
| [`dist/osm.json`](dist/osm.json) | **OpenStreetMap** | Classic OSM Daylight cartography |

---

## 🗺️ Interactive Comparison Viewer

An interactive web application is available live at **[https://markmclaren.github.io/map-styles/](https://markmclaren.github.io/map-styles/)** (hosted via [`docs/`](docs/)) for inspecting and comparing styles side-by-side:

### Features:
- **Single Mode**: Full-screen exploration of any style.
- **Split Mode**: Synchronized side-by-side comparison between styles and baseline references.
- **Swipe Mode**: Interactive draggable divider comparing layers in real time.
- **Location Presets**: London, Edinburgh, Lake District (relief), Swiss Alps (relief), and New York City.
- **JSON Inspector**: View and download active style JSONs with one click.

### Live Demo:
Explore the styles live: **[https://markmclaren.github.io/map-styles/](https://markmclaren.github.io/map-styles/)**

### How to Run Locally:
```bash
# Start a local static server
python3 -m http.server 8080
```
Open **[http://localhost:8080/docs/index.html](http://localhost:8080/docs/index.html)** in your browser.

---

## 🛠️ Toolchain & Scripts

- **[`scripts/compile_styles.py`](scripts/compile_styles.py)**: Compiles the cartographic themes onto the OpenFreeMap vector tile schema and outputs to `dist/`.

To recompile all styles:
```bash
python3 scripts/compile_styles.py
```

---

## 💻 Usage Example (MapLibre GL JS)

```javascript
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

// Load any style:
const map = new maplibregl.Map({
  container: 'map',
  style: 'dist/light-gray.json', // or dark-gray, navigation, modern-antique, etc.
  center: [-0.1276, 51.5074], // London
  zoom: 12
});

// For sandwiching thematic data between Base & Reference:
// 1. Set style to 'dist/light-gray-base.json'
// 2. Add your thematic GeoJSON / vector tile layer
// 3. Add 'dist/light-gray-ref.json' as an overlay or load unified style
```