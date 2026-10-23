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

### 4.5 The Slot-Machine "HOLD" System (One-Armed Bandit Mechanics)
Inspired by arcade fruit machines ("one-armed bandits"), every token card features an interactive **`HOLD`** button:

```
┌──────────────────────────────────────────────────────────────────┐
│  🏞️  Canvas                      [🔒 HELD]  [ 🎨 ] [ #f8fafc ]  │
│      Base terrain                                                │
└──────────────────────────────────────────────────────────────────┘
```

1. **Reel Freezing**: Clicking **`HOLD`** toggles an amber-gold lock state (`.is-held`). When locked, that specific token is completely immune to shuffling.
2. **Anchor Seed Extraction**: When shuffling with held tokens, the harmony engine analyzes the held colors (prioritizing the transportation network or water) to extract an **Anchor Seed Hue ($\theta_0$)**.
3. **Contextual Reshuffling**: The unheld reels spin and generate harmonious colors strictly designed to complement and harmonize with the held colors.
4. **Dynamic Toolbar States**:
   - The shuffle button dynamically tracks reel status: `Shuffle 🎰` $\to$ `Shuffle 🎰 (1 Held)` $\to$ `Shuffle 🎰 (2 Held)`.
   - When any tokens are held, a prominent **`Release Holds (N)`** button appears to clear all locks with a single click.

---

### 4.6 Geometric Color Wheel Harmonies in Cartography
The Style Studio integrates classical color theory into map compilation via `StyleEngine.generateHarmoniousPalette()`. Users can select from 6 distinct geometric harmonies on the $360^\circ$ color circle:

```
      Complementary (180°)                Triadic (120°)                Split-Complementary
            [Roads]                          [Roads]                          [Roads]
               │                                /  \                            /  \
               │                               /    \                          /    \
               │                              /      \                        /      \
            [Canvas]                     [Canvas]  [Parks]               [Water]    [Parks]
                                                                            \      /
                                                                             [Canvas]
```

| Harmony Model | Color Wheel Angles | Cartographic Allocation Strategy | Visual Character & Best Use Cases |
|---|---|---|---|
| **Triadic** | $\theta_0$, $\theta_0 + 120^\circ$, $\theta_0 + 240^\circ$ | Ground at $\theta_0$, Roads at $+120^\circ$, Parks/Water at $+240^\circ$ | **Maximum Cartographic Balance**. The gold standard for general-purpose reference and city navigation maps. Features never conflict. |
| **Complementary** | $\theta_0$, $\theta_0 + 180^\circ$ | Ground/Water at $\theta_0$, Highway network at $\theta_0 + 180^\circ$ | **Maximum Chromatic Tension**. Perfect for motoring atlases and high-glance GPS navigation where highways must instantly jump forward. |
| **Split-Complementary** | $\theta_0$, $\theta_0 + 150^\circ$, $\theta_0 + 210^\circ$ | Ground at $\theta_0$, Roads at $+150^\circ$, Water/Parks at $+210^\circ$ | **Nuanced Editorial Contrast**. Delivers the drama of complementary contrast without harsh vibration. Ideal for web apps and dashboard basemaps. |
| **Analogous** | $\theta_0 - 30^\circ$, $\theta_0$, $\theta_0 + 30^\circ$ | Water at $-30^\circ$, Canvas at $\theta_0$, Parks at $+30^\circ$, Roads deep value step | **Serene Natural Cohesion**. Excellent for environmental, marine, forestry, and minimalist Nordic/Scandinavian themes. |
| **Square** | $\theta_0$, $\theta_0 + 90^\circ$, $\theta_0 + 180^\circ$, $\theta_0 + 270^\circ$ | 4 hues evenly spaced at $90^\circ$ across the wheel | **Dynamic Tetrahedral Balance**. Ideal for rich complex maps with varied POI, transport, and water categorizations. |
| **Monochromatic** | Single Hue $\theta_0$ ($\Delta\theta = 0^\circ$) | Strict luminance stepping across the 6 planes ($L = 97\% \to 10\%$) | **Architectural & Archival Maps**. High-end single-color maps (blueprint cyan, sepia parchment, indigo wash). |
| **Custom** | Unconstrained individual pin coordinates | Independent manual dragging of all 6 nodes | **Total Creative Freedom**. Free-form manual placement for unique or unconventional cartographic palettes. |

---

### 4.7 The Interactive Adobe-Style Color Wheel
Inspired by **[Adobe Color](https://color.adobe.com/create/color-wheel)**, the Style Studio features an interactive circular **Color Wheel Widget** (`#colorWheelSection`):

```
                       0° (Red)
                          ▲
                          │     [🚗 Roads 🎯]
         270° (Purple) ───┼─── 90° (Yellow-Green)
                          │   \
            [🌊 Water]    ▼    [🌲 Parks]
                      180° (Cyan)
```

1. **Polar Coordinate Chromatic Disc**:
   - The wheel disc maps colors in polar coordinates:
     $$\theta = H \quad (\text{Angle from } 0^\circ \text{ to } 360^\circ)$$
     $$r = \frac{S}{100} \cdot R \quad (\text{Radial distance from center } r=0 \text{ to edge } r=R)$$
   - The canvas renders a high-DPI anti-aliased saturation disc at $L=50\%$ pure chroma.
2. **Interactive Semantic Nodes & Harmony Spokes**:
   - Each of the 6 tokens is rendered as an interactive node with its semantic icon (🏞️, 🌊, 🌲, 🚗, 🏢, 🔤) and color fill.
   - Clicking any pin immediately selects that token and opens the **Distinct Colour Popover** picker.
   - White dashed spokes connect each pin to the wheel center, and a semi-transparent geometric polygon connects the active harmony vertices.
3. **Base Color Anchor (🎯 Base) & Discrete Harmony Rotation**:
   - Any token can be designated as the **Base Color Anchor** (via the `🎯 BASE` button atop each cog or the cabinet dropdown).
   - Rotating the harmony is executed cleanly without fussy dragging using dedicated side-to-side buttons (`◀` / `▶` or keyboard shortcuts `[` / `]`), stepping all unheld tokens in calibrated $15^\circ$ increments around the circle while strictly preserving their harmonic intervals (e.g. $180^\circ$ for Complementary, $120^\circ$ for Triad, $\pm 30^\circ$ for Analogous).
4. **Integration with Slot-Machine "HOLD" 🔒**:
   - Any token marked with **HOLD** shows an illuminated lock badge directly on its wheel pin.
   - When harmonies are rotated or randomized, held pins remain locked in place.
5. **Integrated Slot Machine Cabinet, Cog Controls & Distinct Colour Popover**:
   - The Theme Mode toggle (**Light** / **Dark**) and sound mute are positioned directly at the top of the slot machine cabinet.
   - Lightness is tuned directly per-feature on each reel cog using perceptual $L^*$ stepping buttons (`▲` / `▼`).
   - The Base Color Anchor is selectable directly above each cog with `🎯 BASE` or via the cabinet base dropdown.
   - **Distinct Colour Popover (No Drag and Drop)**: Clicking any cog reel's color chip or hex input opens an anchored modal overlay featuring 48 curated, distinct cartographic colors categorized into **Accents & Primaries**, **Soft Fills & Naturals**, and **Neutrals & Monochromes**, with real-time WCAG contrast scoring and custom hex input.
   - **Colour Harmony Cycle & Spin Buttons (`◀` / `▶`)**: Positioned directly beside the Colour Harmony dropdown, these step to the previous or next harmony rule and automatically execute a spin to update unheld reels in real time.
   - **Wheel Rotation Buttons (`-15°` / `+15°`, keys `[` / `]`)**: Positioned beneath the color wheel disc, these rotate the active harmony angles across the $360^\circ$ circle in $15^\circ$ increments.
   - Smart automation actions (**Fix contrast**, **Mono lock**, and **Release holds**) are integrated directly into the slot machine cabinet deck.


---

### 4.8 Mode-Locked Shuffle Engine
Clicking the **Shuffle 🎰** button generates harmonious, balanced color relationships strictly bound to the active **Light** or **Dark** mode:
- If **Dark Mode** is active, canvases remain deep ($L \approx 6\%$) with high-saturation neon/pastel road accents ($L \approx 70\%$) and crisp white labels.
- If **Light Mode** is active, canvases remain airy ($L \approx 97\%$) with deep road vectors ($L \approx 38\%$) and dark slate text.
- **The Shuffle engine never flips between light and dark modes unpredictably.**

---

### 4.9 Deep Dive: How the Palette Machine Operates Under the Hood

To understand why the Palette Machine produces clean, professional cartography rather than a chaotic clash of random colors, we examine the four interlocking mathematical and cartographic subsystems operating on every spin:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THE SPIN PIPELINE IN 5 PHASES                   │
├────────────────────────────────────────────────────────────────────────┤
│ 1. ANCHOR EXTRACTION     Identify the Base Anchor Hue (θ₀)             │
│                          from the selected Base token or held reels.   │
│                                      │                                 │
│ 2. HARMONIC ROTATION     Calculate the 6 entity hues across the 360°   │
│                          wheel using geometric color-theory angles.   │
│                                      │                                 │
│ 3. PHOTOMETRIC SOLVER    Solve lightness and saturation using spatial  │
│                          frequency budgets & WCAG contrast algebra.    │
│                                      │                                 │
│ 4. REEL DRUM ANIMATION   Spin unheld reels to target colors and        │
│                          score the 5 contrast paylines on the marquee. │
│                                      │                                 │
│ 5. MAP COMPILATION       Derive 35+ layer rules and hot-patch the      │
│                          live MapLibre vector style in real time.      │
└────────────────────────────────────────────────────────────────────────┘
```

#### 1. What Effect the Chosen "Base" Colour Makes
In classical color theory and cartographic design, harmonies cannot exist in a vacuum; they must be measured relative to a designated **Root Angle** or **Keynote**. In the Palette Machine, the **Base Colour (`🎯 BASE`)** acts as that keynote ($\theta_0 \in [0^\circ, 360^\circ)$):

- **The Harmonic Root ($\theta_0$)**: When you set an entity as **Base** (e.g. Roads, Water, or Canvas), its hue angle becomes the zero-degree point from which all other angles are measured.
- **Spinning with Unheld Base**: If the Base token is not held, spinning picks a new random $\theta_0$ across the wheel, and all 6 entities rotate together into a fresh color world while preserving their mutual geometric harmony.
- **Spinning with Held Base**: If you lock the Base token with **`HOLD`**, $\theta_0$ is frozen. Spinning generates fresh, harmonious complementary or triadic choices for the unheld features that are mathematically guaranteed to match your chosen base.
- **Interactive Harmony Steering**: On the interactive Color Wheel, the Base token is designated with the `🎯` badge. Dragging the Base pin acts like a steering wheel—it rotates all unheld pins synchronously around the wheel. In contrast, dragging any non-base pin rotates only that single feature.

#### 2. How the Colour Harmonies Come Into Play
When the machine spins, it applies the selected **Harmony Model** to assign specific hue angles to each of the 6 map features:

| Harmony Model | Geometric Angle Formula | Entity Allocation Strategy | Cartographic Behavior |
|---|---|---|---|
| **Triadic** (Default) | $\theta_0$, $\theta_0 + 120^\circ$, $\theta_0 + 240^\circ$ | **Roads** at $\theta_0 + 120^\circ$, **Water** at $+35^\circ$ or $+240^\circ$, **Parks** at $+240^\circ$, **Ground/Buildings** at $\theta_0$ | **Triangular Equilibrium**. Ensures the three primary visual planes (land, water, and highways) each occupy distinct 120° thirds of the spectrum. |
| **Complementary** | $\theta_0$, $\theta_0 + 180^\circ$ | **Roads** at $\theta_0 + 180^\circ$ (direct opposite), **Ground/Buildings/Water** clustered around $\theta_0$ | **Maximum Figure-Ground Pop**. The transportation network directly opposes the landcover, making highways instantly cut through the map. |
| **Split-Complementary** | $\theta_0$, $\theta_0 + 150^\circ$, $\theta_0 + 210^\circ$ | **Roads** at $\theta_0 + 150^\circ$, **Parks/Water** at $\theta_0 + 210^\circ$, **Ground** at $\theta_0$ | **Softened Tension**. Delivers high contrast for roads without the visual vibration of a pure 180° opposite. |
| **Analogous** | $\theta_0 \pm 35^\circ$ | **Water** at $-30^\circ$, **Canvas** at $\theta_0$, **Roads** at $+15^\circ$, **Parks** at $+35^\circ$ | **Monochromatic Mood**. All features share neighboring wavelengths. Contrast is achieved through luminance rather than hue clash. |
| **Square & Tetradic** | $\theta_0 + 90^\circ, 180^\circ, 270^\circ$ | 4 distinct hues distributed evenly across water, roads, parks, and land | **Rich Civic Palette**. Suitable for complex metropolitan maps with dense zoning. |
| **Monochrome** | $\theta_0$ (All hues identical) | Every token set to $\theta_0$; relies strictly on luminance steps ($L = 6\% \to 100\%$) | **Architectural & Archival**. Blueprints, sepia prints, and minimalist night maps. |

#### 3. Why Some Entities Seem Much More Colourful and "Random" Than Others
Users frequently notice that **Roads** and **Water** often appear bright and colorful, while **Canvas**, **Buildings**, and **Parks** remain subdued or neutral. This is not accidental—it is governed by the **Cartographic Saturation and Area Law**:

##### A. The Area vs. Saturation Rule (Spatial Frequency in Vision)
- **Canvas (70%–80% of screen area)**: Large polygon fills must have low saturation ($S \le 16\%$ in Light Mode, $S \le 25\%$ in Dark Mode). If the ground canvas were set to high saturation (e.g. 80% saturated red or yellow), the map would cause severe optical fatigue and vibration.
- **Buildings & Greenspace (10%–20% of screen area)**: As secondary polygon fills, their job is background texture. Their saturation is budgeted moderately ($18\% \le S \le 32\%$) with low contrast against the land ($CR \approx 1.16\text{--}1.35:1$).
- **Roads (< 2% of screen area)**: Roads are thin linear vectors ($1\text{--}3\text{px}$ wide). Due to the high spatial frequency of thin lines, human vision requires **dramatically higher saturation ($S \ge 80\text{--}90\%$)** and **high contrast ($CR \ge 5.5\text{--}8.5:1$)** for the network to remain visible and recognizable at a glance.
- **Labels / Typography**: High contrast ($CR \ge 15.0:1$) with moderate saturation ($25\text{--}40\%$) guarantees crisp WCAG AAA legibility without letterform color bleeding.

##### B. Why Roads Jumps Across Colors While Buildings Stays Steady
- In the harmony engine, **Roads** is explicitly assigned the primary accent angle (e.g. $+120^\circ$ in Triadic, $+180^\circ$ in Complementary). When you spin, Roads sweeps across vibrant complementary hues (e.g. from hot orange to electric cyan).
- **Buildings**, on the other hand, is deliberately anchored to the canvas ground hue ($\theta_{canvas}$) in most harmonies. A city map where each building has an independent random hue looks like confetti noise; keeping buildings harmonic with the ground preserves architectural elegance.
- **Target Luminance Jitter**: The solver applies a small randomized jitter factor:
  $$\text{jitter}(r) = 1 + (r - 1) \cdot (0.88 + \text{rand}(0.24))$$
  Because Roads targets a wide contrast ratio ($8.5:1$), a $\pm 12\%$ jitter causes a substantial, noticeable shift in road brightness. For buildings ($1.28:1$), the same $\pm 12\%$ jitter produces a tiny lightness variation of barely $1\%$, keeping the urban footprint calm and stable.

#### 4. The Photometric Contrast Solver (`colorAtContrast`)
Unlike naive randomizers that roll random RGB numbers (often producing muddy, unreadable maps), the Palette Machine **analytically solves for exact WCAG contrast**:

```
Given:
  - Background Canvas Luminance: Y_bg
  - Target Feature Hue: H
  - Feature Saturation Budget: S
  - Target Contrast Ratio: CR (e.g. 5.5:1 for Roads, 1.16:1 for Parks)

Solve for Target Relative Luminance Y:
  If Darker:  Y = (Y_bg + 0.05) / CR - 0.05
  If Lighter: Y = CR * (Y_bg + 0.05) - 0.05

Synthesize Color:
  Binary search or analytical conversion in CIE / HSL space to find
  the exact Hex color with Hue H, Saturation S, and Luminance Y.
```

By separating **Hue** (governed by color harmonies), **Saturation** (governed by map feature area), and **Lightness** (governed by WCAG contrast algebra), every spin of the Palette Machine produces a fresh, visually exciting, yet fully legible and cartographically sound result.

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
- `StyleEngine.generateHarmoniousPalette({ isDark, harmony, currentTokens, held })`: Generates a balanced 6-token palette using color wheel geometry (Triadic, Complementary, Split-Complementary, Analogous, Tetradic, Monochrome) while preserving any slot-machine `held` tokens.
- `StyleEngine.HARMONY_MODES`: Object containing supported harmony keys (`TRIADIC`, `COMPLEMENTARY`, `SPLIT_COMPLEMENTARY`, `ANALOGOUS`, `TETRADIC`, `MONOCHROME`, `RANDOM`).
- `StyleEngine.invertPaletteMode(tokens, targetIsDark)`: Converts palette between Light and Dark mode while preserving hue character.
- `StyleEngine.autoBalanceContrast(tokens)`: Tunes tokens to meet WCAG AA standards.
- `StyleEngine.generateMonochromeTokens(seedHex, isDark)`: Derives a 6-token harmonious monochromatic palette from a single seed color.
- `StyleEngine.randomBalancedPalette(isDark, harmony, currentTokens, held)`: Generates a balanced harmonious palette strictly adhering to the requested mode.

---

## Palette Machine (slot-machine reels)

The token editor is a fruit machine. Each of the six tokens is a 12-faced 3D reel; the colour on the red payline is the live token.

**Reels step in perceptual lightness.** Faces above the payline are lighter and faces below are darker, each one notch of **5 CIE L\*** apart (the small number on each face is its L\*). Because L\* is perceptually uniform, every notch looks like the same amount of change whether the reel is yellow or navy. HSL lightness is not uniform, which is why the old ±8% ladders felt uneven. Drag a reel, scroll over it, use the ▲▼ nudge buttons, or focus it and use the arrow keys.

**Spins are solved for contrast, not picked in HSL.** A spin chooses hues from the selected harmony, then solves each token's luminance exactly for a target contrast ratio against the canvas:

```
darker side:  Y_fg = (Y_canvas + 0.05) / ratio − 0.05
lighter side: Y_fg = ratio × (Y_canvas + 0.05) − 0.05
```

`colorWithLuminance()` then bisects HSL lightness (luminance is monotonic in it) to hit that Y at the chosen hue and saturation. A yellow road and a blue road therefore land with the same visual weight. Small random jitter on the targets keeps spins varied.

**Contrast paylines.** Each reel has a lamp scoring it against the canvas (`CONTRAST_RULES` in `style-engine.js`):

| Reel | Minimum | Basis |
|---|---|---|
| Labels | 4.5:1 (AAA 7:1, gold lamp) | WCAG 2.1 SC 1.4.3 |
| Roads | 3:1 | WCAG 2.1 SC 1.4.11 non-text |
| Water | 1.10:1 | distinguishable fill |
| Buildings | 1.10:1 | distinguishable fill |
| Parks | 1.05:1 | distinguishable fill |

The marquee shows lines passed; **ALL LINES (AAA)** means every line passes and labels reach AAA.

**Fix contrast** uses `ensureContrast()`: tokens that already pass are untouched, and failing tokens move to the nearest (in L\*) colour of the same hue that meets the threshold, on whichever side of the canvas is closer.

**Swatch palette bar.** Native colour pickers are replaced by an Inkscape-style bar docked along the bottom of the map. It shows fixed, distinct swatches: a column each for grey (with pure white and black), slate, stone and 15 hues. Rows are equal steps of CIE L\* (97 → 14), so the row tells you roughly how much contrast a swatch gives. Click a reel (or its colour chip) to choose what you're painting, then click a swatch, or drag any swatch straight onto a reel. Swatches with a red slash would break that reel's contrast line; for the canvas, a slash means at least one line would fail. The six small swatches at the left are the live palette, so you can drag one reel's colour onto another. Hex fields stay on each reel for exact values.

**Controls:** pull the lever, press SPIN, or hit Space. Set the **Base Colour** directly via the 🎯 BASE button on any cog or via the Base selector in the cabinet deck. ▲▼ nudge lightness on each cog in perceptual CIE L\* steps. HOLD (or keys 1–6) locks a reel. The harmony wheel below the cabinet sets hue and saturation by dragging pins; dragging the 🎯 base pin rotates the whole harmony. Sound effects are off by default (🔇 toggle).
