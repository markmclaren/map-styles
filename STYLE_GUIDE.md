# Cartographic Contrast Style Guide
### Rules for Visual Hierarchy, Layer Separation, and Monochrome Design in MapLibre GL

A practical cartographic reference for designing basemaps on vector tile schemas (such as OpenMapTiles and OpenFreeMap). This guide details **which features must contrast with each other**, the **minimum required luminance separation ($\Delta L$)**, and how to maintain legibility when designing with restricted or single-color (monochrome) palettes.

---

## 1. The 4 Visual Planes of a Map

Cartographic legibility relies on separating map data into four distinct perceptual depth planes. Features on the same plane must harmonize, while features on adjacent planes must contrast sharply.

```
┌──────────────────────────────────────────────────────────────┐
│ Plane 4: Information Overlay (Labels, Badges, POIs)          │  ▲ Top
├──────────────────────────────────────────────────────────────┤  │
│ Plane 3: Structural Vectors (Motorways, Roads, Rails, Borders)│  │
├──────────────────────────────────────────────────────────────┤  │ Depth
│ Plane 2: Urban & Natural Fabric (Parks, Buildings, Landuse)  │  │
├──────────────────────────────────────────────────────────────┤  │
│ Plane 1: Base Canvas (Landcover, Water Bodies, Relief)       │  ▼ Bottom
└──────────────────────────────────────────────────────────────┘
```

* **Plane 1 (Base Canvas)**: Forms the fundamental figure-ground relationship. Low-frequency visual information; must be calm and unobtrusive.
* **Plane 2 (Land Use / Urban Fabric)**: Informs context (parks, residential zones, commercial cores, building footprints). Must remain subordinate to the transportation network.
* **Plane 3 (Transportation & Boundaries)**: The primary structural skeleton. Requires high visual energy, sharp edge definition, and an internal hierarchical order.
* **Plane 4 (Information Overlay)**: Text labels, shields, and symbols. Must achieve maximum contrast against all underlying layers combined.

---

## 2. The Feature Contrast Matrix

The table below lists every critical feature pair in vector cartography, the required separation, the visual mechanism to achieve it, and the consequence of insufficient contrast.

| Feature A (Foreground / Focus) | Feature B (Background / Adjacent) | Minimum Lightness Delta ($\Delta L$ in HSL) | Primary Visual Levers | What Fails if Contrast is Lost |
|---|---|---|---|---|
| **Water** | **Land (Coastlines & Lakes)** | **$\ge 12\%$** (or distinct edge line) | Fill lightness step, 1px coastline stroke (`water_outline`) | Continents, islands, peninsulas, and river mouths vanish; the global map shape dissolves. |
| **Parks / Greenspace** | **Base Land** | **$\ge 5\%$ – $8\%$** | Subtle hue shift, soft tint difference ($\Delta L \approx 6\%$) | Urban recreation areas, national parks, and forests become invisible. |
| **Buildings** | **Urban Land / Parcels** | **$\ge 8\%$ – $12\%$** | Slightly darker fill, 1px building casing outline | City centers lose density definition; 3D footprint geometry flattens into a generic wash. |
| **Local / Minor Roads** | **Base Land** | **$\ge 10\%$ – $15\%$** | Thin stroke (`0.75px – 1.25px`), subtle road casing | Neighborhood street grids disappear, making local navigation and address lookup impossible. |
| **Arterials / Primaries** | **Minor Roads** | **$\ge 15\%$ – $20\%$** | Double stroke width (`2.0px – 3.0px`), saturated fill or distinct value step | Users cannot visually scan cross-town routes through dense neighborhood street grids. |
| **Motorways / Freeways** | **Primary Roads** | **$\ge 15\%$ – $25\%$** | Maximum stroke width (`3.5px – 5.0px`), bold casing (`1.0px – 1.5px`) | Regional highway network loses priority; long-distance corridors blend into surface streets. |
| **Railways** | **Roads** | N/A (Pattern Contrast) | Dashed railway ties / ticks (`line-dasharray: [1.5, 1.5]`), high-contrast dark line | Train lines are mistaken for local roads or tunnels. |
| **Administrative Boundaries** | **Land & Roads** | N/A (Pattern Contrast) | Dash-dot patterns (`[3, 1, 1, 1]`), muted tone without casing | Country/state borders are mistaken for motorways or railways. |
| **Text Labels** | **Any Underlying Feature** | **$\ge 45\%$** (or 2px Halo) | **Text Halo** (2px width matching background canvas), Font Weight (Bold vs Regular) | Labels become illegible when crossing streets, rivers, or park boundaries. |
| **Water Names** | **Water Fill** | **$\ge 25\%$** | *Italic posture*, darker/lighter value of water hue | Ocean, sea, and river labels cannot be read over water bodies. |

---

## 3. The Lightness Budget (Luminance Stepping)

To avoid visual mud, allocate explicit **lightness ranges ($L$)** to feature types. Never allow polygon fills to enter the lightness range reserved for vector strokes.

### Light Themes (Dark-on-Light)

```
0% [Black]                                                            100% [White]
│                                                                                │
▼                                                                                ▼
├── Labels (0–20%)
├──── Major Highways (20–40%)
├────── Secondary Roads (40–60%)
├──────── Minor Roads & Casings (60–75%)
├────────── Water Bodies (75–84%)
├──────────── Parks & Woods (85–92%)
├────────────── Urban Land & Buildings (88–94%)
└──────────────── Base Land Canvas (95–99%)
```

* **Canvas Polygons (Base, Parks, Water)**: Must stay within the **75% – 99%** lightness band.
* **Transportation Vectors (Casings, Fills)**: Must span the **20% – 75%** band to establish rank.
* **Typography & Shields**: Must stay below **20%** lightness to guarantee high contrast.

### Dark Themes (Light-on-Dark)

```
0% [Black]                                                            100% [White]
│                                                                                │
▼                                                                                ▼
├── Base Land Canvas (6–12%)
├──── Water Bodies (10–16%)
├────── Parks & Forests (14–20%)
├──────── Buildings & Urban Fabric (18–24%)
├────────── Minor Roads (28–40%)
├──────────── Secondary Roads (45–65%)
├────────────── Major Highways (70–90%)
└──────────────── Labels & Badges (85–100%)
```

---

## 4. Monochrome (Single-Color) Blueprint

A common misconception is that a monochrome map lacks contrast. In reality, locking **Hue** ($H$) and **Saturation** ($S$) forces strict reliance on **Lightness** ($L$) and **Stroke Geometry**, producing exceptionally clear cartography.

Here is the exact formula for a fully functional single-color map using **Indigo ($H = 215^\circ$, $S = 30\%$)**:

| OpenMapTiles Layer | Type | HSL Value | Hex Equivalent | Visual Mechanism |
|---|---|---|---|---|
| `background` | background | `hsl(215, 20%, 98%)` | `#f8f9fb` | Ultra-pale base canvas |
| `landcover_wood` / `park` | fill | `hsl(215, 25%, 91%)` | `#e2e7ee` | Soft 7% darker wash |
| `water` | fill | `hsl(215, 35%, 80%)` | `#b5c4d6` | Distinct 18% step below land |
| `water_coastline_edge` | line | `hsl(215, 45%, 65%)` | `#7a99be` | 1px boundary line |
| `building` | fill | `hsl(215, 20%, 89%)` | `#dcdee5` | Distinct building footprint |
| `building_outline` | line | `hsl(215, 25%, 78%)` | `#b8becd` | 0.75px crisp structural edge |
| `transportation_minor` | line | `hsl(215, 30%, 60%)` | `#7b8fa7` | Width: `1.0px` |
| `transportation_secondary` | line | `hsl(215, 40%, 42%)` | `#405c7d` | Width: `2.2px` |
| `transportation_primary` | line | `hsl(215, 50%, 28%)` | `#244163` | Width: `3.2px` |
| `transportation_motorway` | line | `hsl(215, 60%, 15%)` | `#0f2238` | Width: `4.5px`, Casing: `1.2px` |
| `transportation_rail` | line | `hsl(215, 20%, 30%)` | `#3d4957` | Line with white dash ticks |
| `place_city` (Text) | symbol | `hsl(215, 65%, 10%)` | `#091624` | Bold weight, 2px halo `#f8f9fb` |
| `water_name` (Text) | symbol | `hsl(215, 45%, 35%)` | `#315278` | *Italic*, 1.5px halo `#b5c4d6` |

---

## 5. Non-Color Contrast Levers

When colors are limited or muted, use these non-chromatic levers to maintain structure:

### 1. Road Casings (The Outer Outline)
A lighter road fill placed inside a darker casing line creates an optical illusion of elevation (figure-ground pop). Casings allow roads with light fills (e.g. `#ffffff`) to remain visible when crossing light backgrounds (`#fafafa`).

### 2. Line Dashing & Patterns
* **Railways**: Never use a plain solid stroke. Use a solid underlying stroke (`#444444`, width 2px) topped by an alternating tick stroke (`line-dasharray: [1.5, 1.5]`, color `#ffffff`).
* **Footpaths & Trails**: Use high-frequency dashes (`line-dasharray: [1, 2]`) to differentiate from vehicular roads.
* **Administrative Boundaries**: Use Morse-code patterns (`line-dasharray: [4, 1.5, 1, 1.5]`) to indicate national borders.

### 3. Typographic Hierarchy
* **Capitals & Major Cities**: `Noto Sans Bold`, uppercase, tracking `+1.5px`, size `14–18px`.
* **Suburbs & Neighborhoods**: `Noto Sans Regular`, sentence case, size `11–13px`.
* **Natural Features & Water**: `Noto Sans Italic`, generous letterspacing (`+2.0px`), size `10–12px`.
* **The Halo Rule**: Every text symbol must have a text halo with a width of at least `1.5px – 2.0px`. The halo color should match the underlying canvas tone to preserve legibility over vector lines.

---

## 6. Verification Heuristics

Before finalizing any map style, test it against these three benchmarks:

1. **The Squint Test (Macro Hierarchy)**:
   * Squint at the screen until the map blurs.
   * Can you still instantly identify where the ocean ends and land begins?
   * Does the motorway network still stand out over local streets?
   * If the map turns into an indistinguishable gray blob, increase the Lightness Delta ($\Delta L$) between Water, Land, and Highways.

2. **The Grayscale Desaturation Test**:
   * View the map through an accessibility tool or CSS filter (`filter: grayscale(100%)`).
   * If two features that looked different in color now merge into an identical shade of gray, they were relying solely on hue rather than luminance. Adjust their lightness values.

3. **The Density Zoom Check**:
   * Inspect the map at Zoom 5 (Continental), Zoom 11 (Metropolitan), and Zoom 15 (Street level).
   * Ensure that building footprints and minor streets smoothly fade out at lower zooms so they do not overpower highways and city labels.
