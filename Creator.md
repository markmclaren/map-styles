# Minimalist Map Style Studio (`Creator.md`)
### Algorithmic Cartographic Compiler, WCAG 2.1 Accessibility Science, and Tonal Control System

A complete technical, mathematical, and cartographic reference for the **Minimalist MapLibre Style Studio** (`docs/creator.html`). This document explains the architectural principles behind synthesizing production-grade vector map styles from a minimal set of design tokens, the mathematical underpinnings of the **WCAG 2.1 Accessibility Rating**, and the mechanics of the **Hue-Locked Tonal Control Bar**.

---

## 1. System Philosophy: The 6-Token Cartographic Compiler

### The Complexity Trap of Traditional Map Editors
Traditional vector map styling suites (such as Maputnik, Mapbox Studio, or raw QGIS/GeoServer configurations) present designers with 300 to 700 individual style layers. Each layer requires configuring dozens of zoom-dependent interpolate curves, filter expressions, fill colors, stroke widths, casing halos, dash arrays, and opacity stops. 

This leads to several systemic failures:
1. **Cognitive Overload**: Modifying a simple palette requires updating 50+ separate line and polygon rules across multiple zoom stops.
2. **Contrast Incoherence**: Subtle color adjustments frequently break the figure-ground relationship between minor roads, waterlines, and text labels.
3. **Inconsistent Light/Dark Translation**: Inverting a light map to dark mode often results in muddy, illegible typography or unreadable coastlines because color adjustments are applied ad-hoc rather than systematically.

### The 6-Token Solution
The **Minimalist Style Studio** replaces layer-by-layer micro-editing with an **Algorithmic Cartographic Compiler** (`docs/style-engine.js`). The designer controls only **6 semantic design tokens**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        6 SEMANTIC DESIGN TOKENS                        │
├──────────────┬──────────────┬──────────────┬──────────────┬────────────┤
│   CANVAS     │    WATER     │  GREENSPACE  │    ROADS     │ BUILDINGS  │
│  (Plane 1)   │  (Plane 1)   │  (Plane 2)   │  (Plane 3)   │ (Plane 2)  │
├──────────────┴──────────────┴──────────────┴──────────────┴────────────┤
│                              LABELS / TEXT                             │
│                                (Plane 4)                               │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │   Algorithmic Theme Synthesizer (docs/style-engine.js)   │
       │   - Relative luminance & mode detection                  │
       │   - 35+ derived cartographic paint rules                 │
       │   - 5-tier road hierarchy & casing expansion             │
       │   - Ambient halo & label color tuning                    │
       └──────────────────────────────────────────────────────────┘
                                    │
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │     Complete 70+ Layer MapLibre GL JSON Style Output     │
       │     (Ready for MapLibre JS, OpenFreeMap, Leaflet, QGIS)  │
       └──────────────────────────────────────────────────────────┘
```

From these 6 tokens, the engine algorithmically synthesizes over 35 distinct paint variables—including highway casings, arterial ramps, local road fills, railway ties, forest tints, building extrusion outlines, coastline borders, and text halos.

---

## 2. The 6 Semantic Design Tokens

Every feature in the OpenMapTiles / OpenFreeMap schema is mapped to one of the 4 visual depth planes:

| Token Key | Primary Depth Plane | Cartographic Features Governed | Algorithmic Derivations |
|---|---|---|---|
| `canvas` | **Plane 1 (Base Ground)** | Base landcover, background polygon, non-urban terrain wash | Residential landuse, commercial fill, industrial tint, ambient text halo, country borders |
| `water` | **Plane 1 (Water Bodies)** | Oceans, seas, reservoirs, lakes, docks, canals, rivers | Coastline outline (`water_outline`), waterway lines (`waterway_line`), italic water labels |
| `greenspace` | **Plane 2 (Natural Fabric)** | City parks, recreation grounds, national parks, forests, golf courses | Deep forest fill (`wood_fill`), urban park fill (`park_fill`), nature reserve boundaries |
| `roads` | **Plane 3 (Structure)** | Motorways, expressways, primary arterials, secondary roads, street grid | 5-tier road hierarchy, bridge casings, tunnel dashed lines, railway tracks (`rail_line`) |
| `buildings` | **Plane 2 (Urban Fabric)** | 2D building footprints, 3D building extrusions, historic monuments | Roof fill (`building_fill`), building edge casing (`building_outline`), parcel density |
| `text` | **Plane 4 (Information)** | Capital cities, town labels, neighborhood names, road shields, POIs | City labels, country labels, road name labels, POI markers, airport text |

---

## 3. WCAG 2.1 Accessibility Science: How the Rating Works

The Style Studio features an integrated real-time **Accessibility Rating Pill** (e.g. `14.2:1 (AAA)`) in the studio header. This rating measures perceptual visual contrast according to the **W3C Web Content Accessibility Guidelines (WCAG) 2.1 Section 1.4.3 and 1.4.6**.

### 3.1 Step 1: Linearization of sRGB Channels (De-Gamma)
Digital screens do not encode light linearly; they apply an sRGB gamma transfer curve ($\gamma \approx 2.2$). To calculate true physical light emission, each 8-bit color channel ($R, G, B \in [0, 255]$) is converted to an uncompressed linear float $c \in [0.0, 1.0]$:

$$c = \frac{C_{\text{sRGB}}}{255}$$

$$c_{\text{lin}} = \begin{cases} 
\dfrac{c}{12.92} & \text{if } c \le 0.04045 \\
\left(\dfrac{c + 0.055}{1.055}\right)^{2.4} & \text{if } c > 0.04045 
\end{cases}$$

### 3.2 Step 2: Relative Luminance ($L$)
Relative luminance represents the photometric brightness of any color normalized to $1.0$ for the brightest white (`#ffffff`) and $0.0$ for the darkest black (`#000000`).

The human eye does not perceive all light wavelengths equally. Our eyes possess three types of cone photoreceptors, with peak sensitivities in the green and red spectrums and very low sensitivity in the blue spectrum. WCAG 2.1 models this using the **CIE 1931 standard colorimetric observer spectral weighting**:

$$L = 0.2126 \cdot R_{\text{lin}} + 0.7152 \cdot G_{\text{lin}} + 0.0722 \cdot B_{\text{lin}}$$

* **Green ($71.52\%$)**: Contributes the vast majority of perceived brightness.
* **Red ($21.26\%$)**: Contributes moderate luminance.
* **Blue ($7.22\%$)**: Contributes very little to perceived brightness (explaining why pure electric blue `#0000ff` has an extremely dark relative luminance of only $0.0722$).

### 3.3 Step 3: The Contrast Ratio Formula & Ambient Glare
Given the relative luminance of two colors, $L_1$ (the lighter color) and $L_2$ (the darker color) such that $L_1 \ge L_2$, the contrast ratio $CR$ is defined as:

$$CR = \frac{L_1 + 0.05}{L_2 + 0.05}$$

#### Why the $+0.05$ Constant Exists
The $+0.05$ offset represents **ambient display flare (specular surface reflection)**. On physical glass screens (smartphones, automotive dashboard screens, laptops), approximately $5\%$ of external ambient light reflects off the display glass into the user's eye. Even if an OLED pixel emits absolute zero light ($L_2 = 0.0$), the perceived black level under ambient light is effectively $0.05$. 

This prevents mathematical division by zero and ensures contrast ratios accurately reflect physical readability in real-world viewing conditions.

### 3.4 The Three Accessibility Tiers
The studio evaluates text against the base canvas and assigns one of three compliance tiers:

```
0:1                     4.5:1                  7.0:1                  21:1
├─────────────────────────┼──────────────────────┼───────────────────────┤
│          FAIL           │       WCAG AA        │       WCAG AAA        │
│   Illegible / Glare     │   Minimum Standard   │   Optimal Legibility  │
└─────────────────────────┴──────────────────────┴───────────────────────┘
```

| Compliance Tier | Contrast Ratio ($CR$) | Studio Visual Pill | Cartographic Implication |
|---|---|---|---|
| **Fail** | **$< 4.5:1$** | Red Badge (`#ef4444`) | Text fails basic legibility. Place names and street labels wash out under ambient light or on low-end screens. Unusable for navigation. |
| **AA (Pass)** | **$4.5:1 \le CR < 7.0:1$** | Green Outline (`#10b981`) | Complies with WCAG 2.1 Level AA for standard body text. Suitable for general-purpose web maps viewed indoors. |
| **AAA (Enhanced)** | **$CR \ge 7.0:1$** | Solid Emerald (`#059669`) | High-contrast certification. Readable under direct outdoor sunlight, by low-vision users, and during high-speed in-car glance navigation. |

### 3.5 Cartographic Multi-Plane Contrast Rules
Unlike flat web pages where text sits on a uniform button, map labels overlay an intricate tapestry of land, water, parks, and road ribbons. The Style Engine enforces contrast across multiple visual planes:

1. **Plane 4 vs Plane 1 (Text vs Canvas)**: Must achieve $\ge 4.5:1$ (AA) or $\ge 7.0:1$ (AAA).
2. **Plane 3 vs Plane 1 (Roads vs Canvas)**: Evaluated against WCAG Non-Text Graphical Object Contrast ($\ge 3.0:1$). The primary road network must remain immediately distinguishable from the background canvas.
3. **Plane 1 vs Plane 2 (Fills: Water / Greenspace / Buildings vs Canvas)**: Evaluated by luminance stepping ($\Delta L \ge 1.25:1$ or $\ge 12\%$ HSL delta). If water and land have identical luminance, coastlines vanish and continents lose their geographic identity.
4. **The Cartographic Halo Failsafe**: Whenever a label passes over a contrasting feature (e.g., dark text crossing a dark highway), standard contrast breaks. The Style Engine resolves this by automatically generating a $2.0\text{px}$ text halo matching the background canvas, preserving local contrast around letterforms.

---

## 4. The Tonal Control System: "Darker" & "Lighter" Mechanics

### 4.1 The Failure of Raw RGB Color Pickers
Standard browser color pickers (`<input type="color">`) operate strictly in the RGB color cube. When a designer wants to make an existing blue darker or lighter, adjusting the standard 2D color picker square shifts both **saturation** and **hue**, frequently causing:
- The color to drift into an unintended hue (e.g., shifting navy into dull purple or gray).
- Accidental desaturation, producing washed-out muddy maps.
- Complete loss of harmonic relationships between adjacent features.

### 4.2 Hue-Locked Tonal Architecture
The Style Studio decouples **Lightness ($L$)** from **Hue ($H$)** and **Saturation ($S$)** using the HSL color model:

```javascript
function adjustHsl(hex, deltas = {}) {
  const rgb = hexToRgb(hex);
  const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
  
  // Hue is locked unless explicitly overridden
  const newH = (deltas.h !== undefined) 
    ? (deltas.h < 0 ? (hsl.h + deltas.h + 360) % 360 : deltas.h) 
    : hsl.h;
    
  // Saturation and Lightness are clamped strictly between 0% and 100%
  const newS = clamp(hsl.s + (deltas.s || 0), 0, 100);
  const newL = clamp(hsl.l + (deltas.l || 0), 0, 100);
  
  const newRgb = hslToRgb(newH, newS, newL);
  return rgbToHex(newRgb.r, newRgb.g, newRgb.b);
}
```

### 4.3 The Tonal Control Bar
Every token card in the Studio contains an interactive **Tonal Control Bar**:

```
┌──────────────────────────────────────────────────────────────────┐
│  [▼ Darker]   ( -16% ) ( -8% ) [ 0% ] ( +8% ) ( +16% )  [▲ Lighter]│
└──────────────────────────────────────────────────────────────────┘
```

1. **Micro-Stepper Buttons (`▼ Darker` / `▲ Lighter`)**:
   - `▼ Darker`: Nudges the token by exactly $-8\%$ Lightness while holding Hue and Saturation strictly locked.
   - `▲ Lighter`: Nudges the token by exactly $+8\%$ Lightness.
2. **The 5-Step Tonal Ladder**:
   - Computes a discrete 5-swatch palette around the token's current value:
     $$\Delta L \in \{-16\%, -8\%, 0\%, +8\%, +16\%\}$$
   - The center chip (`0%`) indicates the currently active color with an active outline.
   - Clicking any chip immediately updates the map style, syncs the hex code input, and recalculates the WCAG contrast score.

### 4.4 Algorithmic Theme Inversion (`invertPaletteMode`)
When switching between **Light** and **Dark** modes via the dedicated header buttons, the system does not simply invert RGB values (which produces unnatural inverted negative colors). Instead, `invertPaletteMode` preserves the user's specific hue palette while transposing the **Lightness Budget**:

| Token | Light Mode Target Range | Dark Mode Target Range | Inversion Logic |
|---|---|---|---|
| **Canvas** | $L \approx 97\%$, $S \le 20\%$ | $L \approx 7\%$, $S \le 25\%$ | Retains ground hue, drops luminance into deep matte ground. |
| **Water** | $L \approx 80\%$, $S \approx 30\text{--}55\%$ | $L \approx 14\%$, $S \approx 30\text{--}60\%$ | Retains water hue, separates from dark land by $+7\%$ lightness. |
| **Greenspace** | $L \approx 90\%$, $S \le 35\%$ | $L \approx 11\%$, $S \le 35\%$ | Soft natural park tint against canvas. |
| **Roads** | $L \approx 38\%$, $S \ge 40\%$ | $L \approx 70\%$, $S \ge 65\%$ | Light roads invert to luminous vectors; saturation is boosted to pop against dark canvas. |
| **Buildings** | $L \approx 86\%$, $S \le 20\%$ | $L \approx 16\%$, $S \le 25\%$ | Urban silhouette sits midway between canvas and minor roads. |
| **Text** | $L \approx 12\%$, $S \le 40\%$ | `#ffffff` ($L = 100\%$) | Inverts from near-black to crisp white for maximum legibility. |

### 4.5 Mode-Locked Shuffle Engine
Clicking the **Shuffle** button generates harmonious, balanced color relationships using triadic and complementary color theory. The generator is strictly bound to the active mode:
- If **Dark Mode** is active, `randomBalancedPalette(true)` generates deep canvases ($L \approx 6\%$) with high-saturation neon/pastel road accents ($L \approx 68\%$) and crisp white labels.
- If **Light Mode** is active, `randomBalancedPalette(false)` generates airy canvases ($L \approx 97\%$) with deep road vectors ($L \approx 42\%$) and dark slate text.
- **The Shuffle engine never flips between light and dark modes unpredictably.**

---

## 5. Style Engine Compiler Architecture

The style compiler takes a clean MapLibre base template (`dist/bright.json` or bundled `docs/dist/bright-template.js`) and transforms it into the final stylesheet:

```
Template JSON (70+ layers)  +  Theme Config (35+ derived rules)
                            │
                            ▼
              compileMapLibreStyle(template, theme)
                            │
                            ├── 1. Background layer -> theme.background
                            ├── 2. Water polygons -> theme.water_fill
                            ├── 3. Coastlines -> theme.water_outline (width 0.75px)
                            ├── 4. Waterways -> theme.waterway_line
                            ├── 5. Natural landuse -> theme.wood_fill / theme.park_fill
                            ├── 6. Urban landuse -> residential / commercial / industrial
                            ├── 7. Buildings -> theme.building_fill & outline
                            ├── 8. Road network (Motorway -> Secondary -> Minor -> Paths)
                            ├── 9. Railway network with cross-tie tick pattern
                            ├── 10. Boundaries -> Country dash [3, 1, 1, 1], State dash
                            └── 11. Typography -> Text color, halo color, halo width (2px)
                            │
                            ▼
           Ready-to-render MapLibre GL Style Object
```

### 5.1 Road Hierarchy Compilation Table
The compiler expands the single `roads` token into a complete 5-tier transportation hierarchy:

| Road Classification | OpenMapTiles `class` Filter | Light Mode Fill | Light Mode Casing | Dark Mode Fill | Dark Mode Casing |
|---|---|---|---|---|---|
| **Motorway / Freeway** | `motorway`, `trunk` | `roads` (Base) | `roads` ($-22\% L$) | `roads` (Base) | `roads` ($-30\% L$) |
| **Primary Arterial** | `primary` | `roads` ($+10\% L$) | `roads` ($-16\% L$) | `roads` ($-10\% L$) | `roads` ($-35\% L$) |
| **Secondary Road** | `secondary` | `roads` ($+22\% L$) | `canvas` ($-18\% L$) | `roads` ($-20\% L$) | `canvas` ($+8\% L$) |
| **Minor / Street Grid** | `minor`, `service` | Pure `#ffffff` | `canvas` ($-15\% L$) | `canvas` ($+25\% L$) | `canvas` ($+5\% L$) |
| **Pedestrian Path** | `path`, `footway` | `canvas` ($-25\% L$) | None | `canvas` ($+32\% L$) | None |
| **Railways** | `rail` | `canvas` ($-48\% L$) | Canvas cross-ties | `roads` ($+15\% L$) | Canvas cross-ties |

---

## 6. Curated Preset Palettes

The Style Studio includes curated presets demonstrating the compiler's range:

| Preset Name | Target Vibe | Canvas | Water | Roads | Accent / Hierarchy |
|---|---|---|---|---|---|
| **Nordic Slate** | Clean Scandinavian data canvas | `#f8fafc` | `#cbd5e1` | `#475569` | Cool monochrome slate |
| **Warm Editorial** | High-contrast publishing & print | `#fbf9f4` | `#b9d7ea` | `#d35400` | Burnt orange highways on warm parchment |
| **Powder Blue** | Calm pastel civic cartography | `#f2f6fa` | `#b4d4eb` | `#15486e` | Deep sapphire road network |
| **Cherry Blossom** | Soft botanical aesthetic | `#fbf4f5` | `#dbb3bb` | `#823545` | Wine & plum road network on blush land |
| **1980s Neon** | Synthwave & cyberpunk night map | `#0d021a` | `#16042b` | `#ff007f` | Laser pink highways, electric cyan text |
| **Amethyst Luxury** | High-contrast royal purple theme | `#0c0514` | `#1f0c38` | `#d69eff` | Luminous lavender roads, pure white labels |
| **Oxblood Night** | Deep crimson motoring night map | `#100305` | `#2b060d` | `#ff7897` | High-visibility rose highways |
| **Metropolis Night** | Classic dark automotive navigation | `#16181c` | `#0a1524` | `#eb8923` | High-visibility amber highways on slate |
| **Botanical Sage** | Earthy natural atlas theme | `#f4f8f5` | `#b3d4bb` | `#265e34` | Forest emerald roads, sage water |
| **Copperplate Sepia** | 18th-century archival copperplate engraving | `#faf7f0` | `#d9cbb4` | `#61401b` | Burnt umber line hierarchy |

---

## 7. Studio User Interface & Features

### 7.1 Single-Hue Monochrome Lock
Clicking **Mono Lock** locks the **Hue** ($H$) and **Saturation** ($S$) across all 6 tokens. Any adjustment made to the road or canvas color automatically recalculates the other 5 tokens along a strict perceptual lightness curve:
- **Light Monochrome**: Canvas ($97\%$), Water ($80\%$), Greenspace ($90\%$), Roads ($30\%$), Buildings ($86\%$), Text ($10\%$).
- **Dark Monochrome**: Canvas ($6\%$), Water ($14\%$), Greenspace ($10\%$), Roads ($75\%$), Buildings ($18\%$), Text ($100\%$).

### 7.2 Real-Time Auto-Contrast Balancer
The **Auto-Contrast** button scans the current 6 tokens and programmatically adjusts them to guarantee **WCAG AA compliance ($\ge 4.5:1$)**:
1. Checks Text vs Canvas; if $< 4.5:1$, sets text to pure white (in dark mode) or `#111827` (in light mode).
2. Checks Water vs Canvas; if $< 1.2:1$, boosts or deepens water lightness by $15\text{--}18\%$.
3. Checks Roads vs Canvas; if $< 3.0:1$, amplifies road lightness and saturation.

### 7.3 Projections: 3D Globe & Mercator
The studio supports instant, GPU-accelerated toggling between:
- **Mercator**: Standard planar conformal projection for street-level exploration.
- **3D Globe**: True spherical planetary projection (`map.setProjection({ type: 'globe' })`) with smooth orbital camera controls.

### 7.4 Sharing and Export
- **Share Link**: Serializes the active 6 tokens and camera state into the URL hash (e.g. `#canvas=f8fafc&water=cbd5e1...`), allowing one-click sharing.
- **Raw JSON Inspector**: Displays the compiled 70+ layer MapLibre JSON in an expandable drawer with syntax formatting and one-click clipboard copying.
- **Download Style**: Generates and downloads a production-ready `style.json` file ready to load directly into MapLibre GL JS, Mapbox GL, Leaflet, OpenLayers, or native mobile apps.

---

## 8. Programmatic API Reference (`docs/style-engine.js`)

The style engine can be imported as a standalone module in web applications or Node.js scripts:

```javascript
// 1. Define your 6 tokens
const myTokens = {
  canvas: '#f8fafc',
  water: '#cbd5e1',
  greenspace: '#e2e8f0',
  roads: '#475569',
  buildings: '#e2e8f0',
  text: '#0f172a'
};

// 2. Derive cartographic theme configuration
const themeConfig = StyleEngine.generateThemeConfig(myTokens);

// 3. Compile MapLibre style from base template
const baseTemplate = await fetch('dist/bright.json').then(r => r.json());
const compiledStyle = StyleEngine.compileMapLibreStyle(baseTemplate, themeConfig);

// 4. Initialize MapLibre
const map = new maplibregl.Map({
  container: 'map',
  style: compiledStyle,
  center: [-0.1276, 51.5074],
  zoom: 12
});
```

### Key API Functions
- `StyleEngine.getRelativeLuminance(hex)`: Returns linear luminance float $[0.0, 1.0]$.
- `StyleEngine.getContrastRatio(hex1, hex2)`: Returns contrast ratio float $[1.0, 21.0]$.
- `StyleEngine.adjustHsl(hex, { h, s, l })`: Adjusts color while holding unmentioned channels locked.
- `StyleEngine.invertPaletteMode(tokens, targetIsDark)`: Converts palette between Light and Dark mode while preserving hue character.
- `StyleEngine.autoBalanceContrast(tokens)`: Tunes tokens to meet WCAG AA standards.
- `StyleEngine.generateMonochromeTokens(seedHex, isDark)`: Derives a 6-token harmonious monochromatic palette from a single seed color.
- `StyleEngine.randomBalancedPalette(isDark)`: Generates a balanced harmonious palette strictly adhering to the requested mode.
