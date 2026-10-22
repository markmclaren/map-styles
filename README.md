# Open Vector Map Styles for MapLibre GL (OpenFreeMap)

A collection of open-source vector map styles for **MapLibre GL** powered by free, open vector map tiles from **[OpenFreeMap](https://openfreemap.org/)** (based on the OpenMapTiles schema).

These styles provide a rich range of cartographic themes—**inspired by and designed in the style of existing iconic maps** (including Google Maps, Apple Maps, Ordnance Survey, Michelin, AA, Rand McNally, National Geographic, Stamen, and CARTO), as well as neutral light/dark data canvas backdrops, high-contrast navigation maps, creative aesthetics (parchment, newspaper, cyberpunk nova, colored pencil, blueprint), and relief/topographic views.

> [!NOTE]
> **Cartographic Heritage & Inspiration**: Styles in this collection referencing external mapping services or organizations (such as Google Maps, Apple Maps, Ordnance Survey, Michelin, AA, Rand McNally, National Geographic, Stamen, or CARTO) are independent open-source designs **inspired by and created in the visual style of existing maps**. They recreate their distinctive palettes, visual contrast, and cartographic hierarchies on top of the open [OpenMapTiles](https://openmaptiles.org/) vector tile schema. All trademarks and brand names are property of their respective owners and are mentioned strictly for stylistic identification.

---

## 🎨 Available Basemap Styles (`dist/`)

All compiled MapLibre style JSON files are located in [`dist/`](dist/) and are ready to load into MapLibre GL JS, MapLibre Native, Leaflet, OpenLayers, or QGIS without requiring an API key or token:

| Style File | Cartographic Theme | Description |
|---|---|---|
| **Consumer Maps & Web Classics** | | |
| [`dist/google-maps-modern.json`](dist/google-maps-modern.json) | **Google Maps (2023+ Cool Slate)** | Inspired by Google's late-2023 redesign (deep teal/cyan water `#85c9d6`, cool icy blue-grey land `#e8eaed`, mint-emerald parks `#a8dab5`, and dark slate/blue-gray freeways `#596b79`) |
| [`dist/google-maps.json`](dist/google-maps.json) | **Google Maps (Warm 2014–2023)** | Inspired by Google's Material Design era (warm ivory landcover `#f4f3f0`, soft cyan water `#aad3df`, sage parks, and warm yellow/orange highways `#fed876`) |
| [`dist/google-maps-2009.json`](dist/google-maps-2009.json) | **Google Maps (Pastel 2009–2013)** | Inspired by Google's October 2009 clean redesign (pale powder-blue water `#b5d0d0`, clean off-white land `#f5f5f3`, soft pastel butter-yellow arterials `#fff5a6`, and light golden freeways `#fbd16c`) |
| [`dist/google-maps-retro.json`](dist/google-maps-retro.json) | **Google Maps (Classic 2005–2009)** | Inspired by the original pre-2009 Google Maps design (rich periwinkle water `#99b3cc`, sunny yellow arterials `#fffa73`, golden highways `#f2bf24`, olive parks `#a7cc95`, and bold white streets with dark slate casings) |
| [`dist/mapquest-classic.json`](dist/mapquest-classic.json) | **MapQuest Classic (1996–2004)** | Inspired by the nostalgic turn-of-the-millennium MapQuest look (electric cyan water `#66ccff`, pure white ground `#ffffff`, black-outlined yellow/orange interstates, and red boundary lines) |
| [`dist/here-classic.json`](dist/here-classic.json) | **HERE Maps / Nokia (Classic)** | Inspired by Nokia / HERE Maps automotive dashboard navigation (cool titanium gray terrain, vibrant cyan water, and high-visibility neon amber/coral highways) |
| [`dist/apple-maps.json`](dist/apple-maps.json) | **Apple Maps** | Inspired by and in the style of Apple Maps (clean pastel cartography with crisp white roads, soft borders, sky-blue water, and emerald greenspaces) |
| [`dist/bing-maps.json`](dist/bing-maps.json) | **Bing Maps** | Inspired by and in the style of Microsoft Bing Maps (muted gray urban fabric, soft yellow highways, and crisp water) |
| **Motoring & Road Atlases** | | |
| [`dist/michelin.json`](dist/michelin.json) | **Michelin Road Atlas** | Inspired by and in the style of the French Michelin road atlas (canary yellow secondary roads, vivid red motorways, high-contrast white ground) |
| [`dist/aa-atlas.json`](dist/aa-atlas.json) | **AA Road Atlas (UK)** | Inspired by and in the style of the British AA Road Atlas (AA yellow accents, motorway blue, emerald A-roads, and TSRGD shields) |
| [`dist/rand-mcnally.json`](dist/rand-mcnally.json) | **Rand McNally Road Atlas** | Inspired by and in the style of the Rand McNally American Road Atlas (Interstate blue ribbons, US highway red routes, and warm cream land) |
| [`dist/os-landranger.json`](dist/os-landranger.json) | **OS Landranger (1:50k Classic)** | Inspired by the legendary British Ordnance Survey 1:50,000 Landranger series (iconic cerise magenta A-roads `#e60067`, cadmium orange B-roads `#ff7700`, royal blue motorways `#0078d7`, lemon yellow minor roads, and TSRGD road shields) |
| [`dist/swisstopo.json`](dist/swisstopo.json) | **Swisstopo (Swiss National Map)** | Inspired by the Swiss Federal Office of Topography (razor-sharp legibility, glacial blue water `#a0c8e6`, red autobahns `#dd352e`, alpine relief shading, and Swiss typography) |
| [`dist/streetmap.json`](dist/streetmap.json) | **Streetmap UK Classic** | Inspired by and in the style of traditional British street atlases (motorway blue, emerald A-roads, amber B-roads, peach buildings, and TSRGD sign badges) |
| [`dist/streetmap-minimal.json`](dist/streetmap-minimal.json) | **Streetmap UK (Minimal)** | Lightweight standalone starter style containing core essential layers for high-speed street mapping |
| [`dist/os-roads.json`](dist/os-roads.json) | **Ordnance Survey - Roads** | In the style of OS UK road network cartography (peach buildings, cyan motorways, green A-roads) |
| [`dist/navigation.json`](dist/navigation.json) | **Navigation** | High-contrast daytime navigation cartography |
| [`dist/navigation-dark.json`](dist/navigation-dark.json) | **Navigation (Dark)** | Low-glare night navigation cartography |
| **OpenFreeMap Core References** | | |
| [`dist/liberty.json`](dist/liberty.json) | **OpenFreeMap Liberty** | The flagship OpenFreeMap / OSM Liberty basemap with rich POIs, icons, and natural colors |
| [`dist/bright.json`](dist/bright.json) | **OpenFreeMap Bright** | High-clarity light general-purpose basemap with crisp typography and subtle relief |
| [`dist/positron.json`](dist/positron.json) | **OpenFreeMap Positron** | In the style of CARTO Positron light monochrome backdrop designed for data visualization |
| [`dist/fiord.json`](dist/fiord.json) | **OpenFreeMap Fiord** | Elegant Nordic-inspired slate blue & cool gray theme |
| [`dist/dark.json`](dist/dark.json) | **OpenFreeMap Dark** | In the style of CARTO Dark Matter minimalist charcoal night theme |
| **Web-Map Classics & Wildcards** | | |
| [`dist/stamen-toner.json`](dist/stamen-toner.json) | **Stamen Toner** | Inspired by and in the style of Stamen Toner (stark, high-contrast 1-bit black & white cartography with pure black water/buildings and white roads) |
| [`dist/carto-voyager.json`](dist/carto-voyager.json) | **CARTO Voyager** | In the style of CARTO Voyager colorful editorial basemap with soft pastel buildings and warm highway fills |
| [`dist/natgeo.json`](dist/natgeo.json) | **National Geographic Atlas** | Inspired by and in the style of the National Geographic Atlas (warm parchment tones, shaded relief, olive forests, and colored boundary ribbons) |
| [`dist/modern-antique.json`](dist/modern-antique.json) | **Modern Antique** | Vintage antique parchment map with sepia tones & antique calligraphy feel |
| [`dist/newspaper.json`](dist/newspaper.json) | **Newspaper** | High-contrast editorial black & white / grayscale newspaper print aesthetic |
| [`dist/nova.json`](dist/nova.json) | **Nova** | Cyberpunk dark theme with deep obsidian blue & electric glowing cyan roads |
| [`dist/colored-pencil.json`](dist/colored-pencil.json) | **Colored Pencil** | Whimsical hand-drawn colored pencil & pastel sketch aesthetic |
| [`dist/charted-territory.json`](dist/charted-territory.json) | **Charted Territory** | Vintage exploration atlas map with warm olive greens, tan earth & relief |
| [`dist/midcentury.json`](dist/midcentury.json) | **Midcentury** | 1950s/1960s retro art style featuring turquoise waters, coral highways & mustard accents |
| [`dist/blueprint.json`](dist/blueprint.json) | **Blueprint** | Architectural drafting blueprint styling with deep blueprint blue & white lines |
| **1980s Retro Aesthetics** | | |
| [`dist/eighties-pastel.json`](dist/eighties-pastel.json) | **1980s Pastel (Miami & Memphis)** | Authentic 1980s Memphis/Miami pastel palette with Caribbean turquoise water `#8fe1eb`, mint parks `#b5efd3`, blush buildings, and hot flamingo pink motorways `#ff4081` |
| [`dist/eighties-neon.json`](dist/eighties-neon.json) | **1980s Neon (Synthwave & Cyber)** | 1980s Synthwave/Retrowave arcade aesthetic with blacklight midnight canvas `#0d021a`, glowing electric cyan coastlines `#00f0ff`, laser hot pink freeways `#ff007f`, and neon green rail `#39ff14` |
| **Monochrome (Single-Hue) Series** | | |
| [`dist/monochrome-indigo.json`](dist/monochrome-indigo.json) | **Monochrome Indigo** | Architectural Prussian navy wash locking Hue to 215° with strict luminance stepping across water, roads, and typography |
| [`dist/monochrome-sepia.json`](dist/monochrome-sepia.json) | **Monochrome Sepia** | 18th-century archival copperplate engraving tone (Hue 35°) with warm burnt umber line hierarchy and parchment canvas |
| [`dist/monochrome-emerald.json`](dist/monochrome-emerald.json) | **Monochrome Emerald** | Botanical forest green wash (Hue 155°) providing crisp natural separation across urban blocks, roads, and hydrography |
| [`dist/monochrome-amber.json`](dist/monochrome-amber.json) | **Monochrome Amber** | High-contrast vintage darkroom warm ochre/amber palette (Hue 42°) engineered for maximum legibility |
| [`dist/monochrome-purple.json`](dist/monochrome-purple.json) | **Monochrome Purple** | Deep dark amethyst / aubergine night theme (Hue 280°) with glowing lilac highway spines and crisp lavender labels |
| [`dist/monochrome-crimson.json`](dist/monochrome-crimson.json) | **Monochrome Crimson** | Deep dark oxblood / burgundy wine theme (Hue 350°) with illuminated rose-coral arterial ribbons and pale pink typography |
| [`dist/monochrome-pink.json`](dist/monochrome-pink.json) | **Monochrome Soft Pink** | Soft blush & dusty rose wash (Hue 348°) pairing delicate pastel canvas tones with rich rosewood highway spines and crisp plum typography |
| **British & Ordnance Survey (UK)** | | |
| [`dist/os-landranger.json`](dist/os-landranger.json) | **OS Landranger (1:50k Classic)** | Classic Landranger Explorer style with magenta A-roads, orange B-roads, and blue motorways |
| [`dist/os-outdoor.json`](dist/os-outdoor.json) | **Ordnance Survey - Outdoor** | In the style of classic OS Landranger/Explorer outdoor styling with greenspaces & relief |
| [`dist/os-light.json`](dist/os-light.json) | **Ordnance Survey - Light** | In the style of OS Open Zoomstack Light minimalist backdrop designed for GIS data overlay |
| [`dist/os-zoomstack-night.json`](dist/os-zoomstack-night.json) | **Ordnance Survey - Night** | In the style of OS Open Zoomstack Night theme with deep obsidian backdrop and glowing cyan/orange roads |
| [`dist/os-deuteranopia.json`](dist/os-deuteranopia.json) | **OS Deuteranopia (Accessible)** | In the style of OS Zoomstack Deuteranopia for red-green color vision deficiency (purples/blues/ambers) |
| [`dist/os-tritanopia.json`](dist/os-tritanopia.json) | **OS Tritanopia (Accessible)** | In the style of OS Zoomstack Tritanopia for blue-yellow color vision deficiency (rose/teal/charcoal) |
| **OSM & Transit Ecosystem** | | |
| [`dist/osm-carto.json`](dist/osm-carto.json) | **OpenStreetMap Standard (OSM Carto)** | The official OpenStreetMap Mapnik standard stylesheet (salmon-red motorways `#e990a0`, amber A-roads `#fdbf6f`, pale yellow B-roads `#f7fabf`, and powder blue water `#aad3df`) |
| [`dist/humanitarian.json`](dist/humanitarian.json) | **Humanitarian (HOT)** | In the style of Humanitarian OpenStreetMap Team (HOT) with coral-pink highways, soft blue water, and highlighted facilities |
| [`dist/transport-transit.json`](dist/transport-transit.json) | **Thunderforest Transport** | Inspired by and in the style of Thunderforest Transport and classic transit maps with prominent rail/subway lines |
| [`dist/osm.json`](dist/osm.json) | **OpenStreetMap** | Classic OpenStreetMap Daylight cartography |
| [`dist/streets.json`](dist/streets.json) | **Streets** | Classic street map styling |
| [`dist/streets-night.json`](dist/streets-night.json) | **Streets (Night)** | Low-light night street cartography |
| [`dist/community.json`](dist/community.json) | **Community** | Vibrant municipal cartography highlighting civic parks, paths & campuses |
| **Thematic Data & Canvas** | | |
| [`dist/light-gray.json`](dist/light-gray.json) | **Light Gray Canvas (Unified)** | Muted minimalist background with integrated labels |
| [`dist/light-gray-base.json`](dist/light-gray-base.json) | **Light Gray Canvas (Base)** | Base polygons & lines only (ideal for sandwiching thematic data) |
| [`dist/light-gray-ref.json`](dist/light-gray-ref.json) | **Light Gray Canvas (Reference)** | Overlay labels & boundaries with transparent background |
| [`dist/dark-gray.json`](dist/dark-gray.json) | **Dark Gray Canvas (Unified)** | Dark charcoal neutral theme with integrated labels |
| [`dist/dark-gray-base.json`](dist/dark-gray-base.json) | **Dark Gray Canvas (Base)** | Dark base polygons & lines only |
| [`dist/dark-gray-ref.json`](dist/dark-gray-ref.json) | **Dark Gray Canvas (Reference)** | Dark overlay labels & boundaries |
| [`dist/human-geography.json`](dist/human-geography.json) | **Human Geography** | Ultra-clean neutral light monochrome backdrop designed for thematic overlays |
| [`dist/human-geography-base.json`](dist/human-geography-base.json) | **Human Geography (Base)** | Base layer without labels for sandwiching thematic data layers |
| [`dist/human-geography-dark.json`](dist/human-geography-dark.json) | **Human Geography Dark** | Dark slate/charcoal companion engineered for high-contrast thematic data |
| [`dist/human-geography-dark-base.json`](dist/human-geography-dark-base.json) | **Human Geography Dark (Base)**| Dark base layer without labels for thematic sandwiching |
| **Topography, Relief & Marine** | | |
| [`dist/topographic.json`](dist/topographic.json) | **Topographic** | Traditional contour/relief topographic look |
| [`dist/outdoor.json`](dist/outdoor.json) | **Outdoor** | Recreation map with hiking trails, bike paths, parks & shaded relief |
| [`dist/terrain.json`](dist/terrain.json) | **Terrain** | Physical geography focused on elevation tinting, mountains & relief |
| [`dist/oceans.json`](dist/oceans.json) | **Oceans** | Marine cartography highlighting coastal contours & oceanic features |

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

## 📖 Cartographic Style Guide

For an in-depth reference on visual hierarchy, layer separation, luminance budgets, and single-hue monochrome design rules, see the **[`STYLE_GUIDE.md`](STYLE_GUIDE.md)**.

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
  zoom: 12,
  renderWorldCopies: false // Only show a single copy of the earth
});

// For sandwiching thematic data between Base & Reference:
// 1. Set style to 'dist/light-gray-base.json'
// 2. Add your thematic GeoJSON / vector tile layer
// 3. Add 'dist/light-gray-ref.json' as an overlay or load unified style
```