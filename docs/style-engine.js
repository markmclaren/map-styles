/**
 * style-engine.js
 * Client-Side Algorithmic Cartographic Style Compiler
 * Transforms 6 user design tokens into a full 70+ layer MapLibre GL style.
 */

// --- Color Science Utilities ---

function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

function hexToRgb(hex) {
  if (!hex || typeof hex !== 'string') return { r: 0, g: 0, b: 0 };
  let c = hex.replace(/[^0-9A-Fa-f]/g, '').trim();
  if (c.length === 3) c = c.split('').map(x => x + x).join('');
  if (c.length !== 6) return { r: 0, g: 0, b: 0 };
  const num = parseInt(c, 16);
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255
  };
}

function rgbToHex(r, g, b) {
  const toHex = (n) => clamp(Math.round(n), 0, 255).toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h, s, l = (max + min) / 2;

  if (max === min) {
    h = s = 0; // achromatic
  } else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h *= 60;
  }
  return { h: Math.round(h), s: Math.round(s * 100), l: Math.round(l * 100) };
}

function hslToRgb(h, s, l) {
  h = (h % 360 + 360) % 360;
  s = clamp(s, 0, 100) / 100;
  l = clamp(l, 0, 100) / 100;

  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs((h / 60) % 2 - 1));
  const m = l - c / 2;
  let r = 0, g = 0, b = 0;

  if (0 <= h && h < 60) { r = c; g = x; b = 0; }
  else if (60 <= h && h < 120) { r = x; g = c; b = 0; }
  else if (120 <= h && h < 180) { r = 0; g = c; b = x; }
  else if (180 <= h && h < 240) { r = 0; g = x; b = c; }
  else if (240 <= h && h < 300) { r = x; g = 0; b = c; }
  else if (300 <= h && h < 360) { r = c; g = 0; b = x; }

  return {
    r: Math.round((r + m) * 255),
    g: Math.round((g + m) * 255),
    b: Math.round((b + m) * 255)
  };
}

function adjustHsl(hex, deltas = {}) {
  const rgb = hexToRgb(hex);
  const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
  const newH = (deltas.h !== undefined) ? (deltas.h < 0 ? (hsl.h + deltas.h + 360) % 360 : deltas.h) : hsl.h;
  const newS = clamp(hsl.s + (deltas.s || 0), 0, 100);
  const newL = clamp(hsl.l + (deltas.l || 0), 0, 100);
  const newRgb = hslToRgb(newH, newS, newL);
  return rgbToHex(newRgb.r, newRgb.g, newRgb.b);
}

function getRelativeLuminance(hex) {
  const rgb = hexToRgb(hex);
  const toLin = (c) => {
    c /= 255;
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * toLin(rgb.r) + 0.7152 * toLin(rgb.g) + 0.0722 * toLin(rgb.b);
}

function getContrastRatio(hex1, hex2) {
  const l1 = getRelativeLuminance(hex1);
  const l2 = getRelativeLuminance(hex2);
  const high = Math.max(l1, l2);
  const low = Math.min(l1, l2);
  return (high + 0.05) / (low + 0.05);
}

// --- Algorithmic Theme Synthesizer ---

/**
 * Derives 35+ cartographic paint rules from 6 semantic design tokens.
 * @param {Object} tokens - { canvas, water, greenspace, roads, buildings, text }
 * @returns {Object} full theme config
 */
function generateThemeConfig(tokens) {
  const canvasLum = getRelativeLuminance(tokens.canvas);
  const isDark = canvasLum < 0.2;

  const canvasHsl = rgbToHsl(hexToRgb(tokens.canvas).r, hexToRgb(tokens.canvas).g, hexToRgb(tokens.canvas).b);
  const waterHsl = rgbToHsl(hexToRgb(tokens.water).r, hexToRgb(tokens.water).g, hexToRgb(tokens.water).b);
  const roadsHsl = rgbToHsl(hexToRgb(tokens.roads).r, hexToRgb(tokens.roads).g, hexToRgb(tokens.roads).b);

  // Coastline & Waterway derivation
  const waterOutline = isDark 
    ? adjustHsl(tokens.water, { l: +42, s: +20 }) 
    : adjustHsl(tokens.water, { l: -22, s: +10 });
  const waterwayLine = isDark 
    ? adjustHsl(tokens.water, { l: +48, s: +25 }) 
    : adjustHsl(tokens.water, { l: -24, s: +15 });

  // Urban & Land Fabric
  const woodFill = isDark 
    ? adjustHsl(tokens.greenspace, { l: -4, s: +5 }) 
    : adjustHsl(tokens.greenspace, { l: -6, s: +8 });
  const parkFill = tokens.greenspace;

  const residentialFill = isDark ? adjustHsl(tokens.canvas, { l: +3 }) : adjustHsl(tokens.canvas, { l: -2 });
  const commercialFill = isDark ? adjustHsl(tokens.canvas, { l: +5 }) : adjustHsl(tokens.canvas, { l: -4 });
  const industrialFill = isDark ? adjustHsl(tokens.canvas, { l: +7 }) : adjustHsl(tokens.canvas, { l: -6 });
  const specialFill = isDark ? adjustHsl(tokens.canvas, { l: +5 }) : adjustHsl(tokens.canvas, { l: -4 });
  const sandFill = isDark ? adjustHsl(tokens.canvas, { l: +10, s: +10 }) : adjustHsl(tokens.canvas, { l: -4, s: +15 });
  const glacierFill = isDark ? adjustHsl(tokens.canvas, { l: +14, s: +5 }) : adjustHsl(tokens.canvas, { l: -1, s: +5 });

  // Building Footprints
  const buildingFill = tokens.buildings;
  const buildingOutline = isDark 
    ? adjustHsl(tokens.buildings, { l: +22 }) 
    : adjustHsl(tokens.buildings, { l: -18 });

  // Transportation Network (Roads hierarchy)
  let motorwayFill, motorwayCasing, primaryFill, primaryCasing, secondaryFill, secondaryCasing, minorFill, minorCasing, pathLine, railLine;

  if (isDark) {
    motorwayFill = tokens.roads;
    motorwayCasing = adjustHsl(tokens.roads, { l: -30 });
    primaryFill = adjustHsl(tokens.roads, { l: -10 });
    primaryCasing = adjustHsl(tokens.roads, { l: -35 });
    secondaryFill = adjustHsl(tokens.roads, { l: -20, s: -15 });
    secondaryCasing = adjustHsl(tokens.canvas, { l: +8 });
    minorFill = adjustHsl(tokens.canvas, { l: +25, s: +10 });
    minorCasing = adjustHsl(tokens.canvas, { l: +5 });
    pathLine = adjustHsl(tokens.canvas, { l: +32 });
    railLine = adjustHsl(tokens.roads, { l: +15 });
  } else {
    motorwayFill = tokens.roads;
    motorwayCasing = adjustHsl(tokens.roads, { l: -22 });
    primaryFill = adjustHsl(tokens.roads, { l: +10, s: -5 });
    primaryCasing = adjustHsl(tokens.roads, { l: -16 });
    secondaryFill = adjustHsl(tokens.roads, { l: +22, s: -15 });
    secondaryCasing = adjustHsl(tokens.canvas, { l: -18 });
    minorFill = '#ffffff';
    minorCasing = adjustHsl(tokens.canvas, { l: -15 });
    pathLine = adjustHsl(tokens.canvas, { l: -25 });
    railLine = adjustHsl(tokens.canvas, { l: -48 });
  }

  // Administrative Boundaries
  const boundaryCountry = isDark ? adjustHsl(tokens.canvas, { l: +40 }) : adjustHsl(tokens.canvas, { l: -40 });
  const boundaryState = isDark ? adjustHsl(tokens.canvas, { l: +25 }) : adjustHsl(tokens.canvas, { l: -25 });

  // Typography & Information Overlays
  const labelCity = tokens.text;
  const labelCityHalo = tokens.canvas;
  const labelCountry = isDark ? adjustHsl(tokens.text, { l: -15 }) : adjustHsl(tokens.text, { l: +20 });
  const labelCountryHalo = tokens.canvas;
  const labelWater = isDark ? adjustHsl(tokens.water, { l: +40 }) : adjustHsl(tokens.water, { l: -32 });
  const labelWaterHalo = tokens.water;
  const labelRoad = isDark ? adjustHsl(tokens.text, { l: -10 }) : adjustHsl(tokens.text, { l: +20 });
  const labelRoadHalo = tokens.canvas;
  const labelOther = isDark ? adjustHsl(tokens.text, { l: -10 }) : adjustHsl(tokens.text, { l: +20 });
  const labelPoi = isDark ? adjustHsl(tokens.text, { l: -15 }) : adjustHsl(tokens.text, { l: +25 });

  return {
    isDark,
    background: tokens.canvas,
    land_fill: tokens.canvas,
    water_fill: tokens.water,
    water_outline: waterOutline,
    waterway_line: waterwayLine,
    wood_fill: woodFill,
    park_fill: parkFill,
    residential_fill: residentialFill,
    commercial_fill: commercialFill,
    industrial_fill: industrialFill,
    special_fill: specialFill,
    sand_fill: sandFill,
    glacier_fill: glacierFill,
    building_fill: buildingFill,
    building_outline: buildingOutline,
    motorway_fill: motorwayFill,
    motorway_casing: motorwayCasing,
    primary_fill: primaryFill,
    primary_casing: primaryCasing,
    secondary_fill: secondaryFill,
    secondary_casing: secondaryCasing,
    minor_fill: minorFill,
    minor_casing: minorCasing,
    path_line: pathLine,
    rail_line: railLine,
    include_rail_ticks: true,
    rail_ticks_color: tokens.canvas,
    boundary_country: boundaryCountry,
    boundary_state: boundaryState,
    label_city: labelCity,
    label_city_halo: labelCityHalo,
    label_country: labelCountry,
    label_country_halo: labelCountryHalo,
    label_water: labelWater,
    label_water_halo: labelWaterHalo,
    label_road: labelRoad,
    label_road_halo: labelRoadHalo,
    label_other: labelOther,
    label_poi: labelPoi,
    label_poi_halo: labelCityHalo,
    label_airport: labelPoi
  };
}

/**
 * Transforms a MapLibre base template JSON into a styled output using the theme config.
 * @param {Object} baseTemplate - Clean MapLibre JSON template
 * @param {Object} theme - Derived theme configuration object
 * @returns {Object} Complete ready-to-render MapLibre style JSON
 */
function compileMapLibreStyle(baseTemplate, theme) {
  const style = JSON.parse(JSON.stringify(baseTemplate));
  style.name = theme.name || 'Custom Basemap';

  const newLayers = [];

  for (const layer of (style.layers || [])) {
    const lId = layer.id || '';
    const lType = layer.type || '';
    const sLayer = layer['source-layer'] || '';

    const paint = layer.paint || (layer.paint = {});
    const layout = layer.layout || (layer.layout = {});

    // 1. Background
    if (lType === 'background') {
      paint['background-color'] = theme.background || '#ffffff';
      newLayers.push(layer);
      continue;
    }

    // 2. Waterways
    if ((sLayer === 'waterway' || lId.includes('waterway') || lId.includes('river')) && lType === 'line') {
      paint['line-color'] = theme.waterway_line || theme.water_fill;
    }

    // 3. Water Bodies
    else if ((sLayer === 'water' || lId === 'water' || lId.startsWith('water-') || (lType === 'fill' && lId.includes('water') && !lId.includes('waterway'))) && lType === 'fill') {
      paint['fill-color'] = theme.water_fill;
      if (theme.water_outline) {
        paint['fill-outline-color'] = theme.water_outline;
      }
      newLayers.push(layer);

      // Add high-contrast coastline edge stroke
      if (lId === 'water' && theme.water_outline) {
        newLayers.push({
          id: 'water_coastline_edge',
          type: 'line',
          source: 'openmaptiles',
          'source-layer': 'water',
          paint: {
            'line-color': theme.water_outline,
            'line-width': [
              'interpolate',
              ['exponential', 1.2],
              ['zoom'],
              0, 1.0,
              6, 1.4,
              12, 2.0
            ]
          }
        });
      }
      continue;
    }

    // 4. Landcover / Landuse
    else if (['landcover', 'landuse', 'park'].includes(sLayer) && lType === 'fill') {
      if (['wood', 'forest'].some(w => lId.includes(w))) {
        paint['fill-color'] = theme.wood_fill;
      } else if (['park', 'grass', 'garden'].some(w => lId.includes(w))) {
        paint['fill-color'] = theme.park_fill;
      } else if (['residential', 'suburb'].some(w => lId.includes(w))) {
        paint['fill-color'] = theme.residential_fill;
      } else if (['commercial', 'retail'].some(w => lId.includes(w))) {
        paint['fill-color'] = theme.commercial_fill;
      } else if (['industrial', 'railway'].some(w => lId.includes(w))) {
        paint['fill-color'] = theme.industrial_fill;
      } else if (['cemetery', 'hospital', 'school'].some(w => lId.includes(w))) {
        paint['fill-color'] = theme.special_fill;
      } else if (lId.includes('sand') || lId.includes('beach')) {
        paint['fill-color'] = theme.sand_fill;
      } else if (['glacier', 'ice'].some(w => lId.includes(w)) && !lId.includes('service')) {
        paint['fill-color'] = theme.glacier_fill;
      } else {
        paint['fill-color'] = theme.land_fill;
      }
    }

    // 5. Buildings
    else if (sLayer === 'building' && lType === 'fill') {
      paint['fill-color'] = theme.building_fill;
      if (theme.building_outline) {
        paint['fill-outline-color'] = theme.building_outline;
      }
    }

    // 6. Transportation Network
    else if (sLayer === 'transportation' && lType === 'line') {
      const isCasing = lId.includes('casing');
      let colorKey = 'minor_fill';

      if (['motorway', 'freeway'].some(m => lId.includes(m))) {
        colorKey = isCasing ? 'motorway_casing' : 'motorway_fill';
      } else if (['trunk', 'primary'].some(m => lId.includes(m))) {
        colorKey = isCasing ? 'primary_casing' : 'primary_fill';
      } else if (lId.includes('secondary')) {
        colorKey = isCasing ? 'secondary_casing' : 'secondary_fill';
      } else if (['tertiary', 'minor', 'residential', 'service'].some(m => lId.includes(m))) {
        colorKey = isCasing ? 'minor_casing' : 'minor_fill';
      } else if (['path', 'pedestrian', 'footway', 'cycleway'].some(m => lId.includes(m))) {
        colorKey = 'path_line';
      } else if (['rail', 'transit'].some(m => lId.includes(m))) {
        colorKey = 'rail_line';
      }

      if (theme[colorKey]) {
        paint['line-color'] = theme[colorKey];
      }

      newLayers.push(layer);

      // Add dashed railway ties
      if (lId === 'railway' && theme.include_rail_ticks) {
        newLayers.push({
          id: 'railway_ticks',
          type: 'line',
          source: 'openmaptiles',
          'source-layer': 'transportation',
          filter: [
            'all',
            ['match', ['geometry-type'], ['LineString', 'MultiLineString'], true, false],
            ['==', ['get', 'class'], 'rail']
          ],
          paint: {
            'line-color': theme.rail_ticks_color || '#ffffff',
            'line-width': 1.5,
            'line-dasharray': [1.5, 1.5]
          }
        });
      }
      continue;
    }

    // 7. Boundaries
    else if (sLayer === 'boundary' && lType === 'line') {
      if (['country', 'admin_level_2', 'admin-2'].some(b => lId.includes(b))) {
        paint['line-color'] = theme.boundary_country;
      } else {
        paint['line-color'] = theme.boundary_state;
      }
    }

    // 8. Labels & Symbols
    else if (lType === 'symbol') {
      const defaultHalo = theme.label_city_halo || theme.background || '#ffffff';
      const defaultText = theme.label_road || theme.label_country || theme.label_city || '#444444';

      if (sLayer === 'place') {
        if (['city', 'town', 'village'].some(c => lId.includes(c))) {
          paint['text-color'] = theme.label_city;
          paint['text-halo-color'] = theme.label_city_halo || defaultHalo;
          paint['text-halo-width'] = 1.2;
        } else if (['country', 'state'].some(c => lId.includes(c))) {
          paint['text-color'] = theme.label_country;
          paint['text-halo-color'] = theme.label_country_halo || defaultHalo;
          paint['text-halo-width'] = 1.5;
        } else {
          // Suburbs, quarters, neighborhoods
          paint['text-color'] = theme.label_other || defaultText;
          paint['text-halo-color'] = defaultHalo;
          paint['text-halo-width'] = 1.2;
        }
      } else if (['water_name', 'waterway'].includes(sLayer) || lId.includes('water')) {
        paint['text-color'] = theme.label_water;
        paint['text-halo-color'] = theme.label_water_halo || defaultHalo;
        paint['text-halo-width'] = 1.2;
      } else if (sLayer === 'transportation_name') {
        if (!lId.includes('shield')) {
          paint['text-color'] = theme.label_road;
          paint['text-halo-color'] = theme.label_road_halo || defaultHalo;
          paint['text-halo-width'] = 1.0;
        }
      } else if (['poi', 'poi_transit'].includes(sLayer) || lId.includes('poi')) {
        paint['text-color'] = theme.label_poi || defaultText;
        paint['text-halo-color'] = theme.label_poi_halo || defaultHalo;
        paint['text-halo-width'] = 1.0;
      } else if (sLayer === 'aerodrome_label' || lId.includes('airport')) {
        paint['text-color'] = theme.label_airport || defaultText;
        paint['text-halo-color'] = defaultHalo;
        paint['text-halo-width'] = 1.0;
      } else {
        if ('text-halo-color' in paint) paint['text-halo-color'] = defaultHalo;
        if ('text-color' in paint) paint['text-color'] = defaultText;
      }
    }

    newLayers.push(layer);
  }

  style.layers = newLayers;
  return style;
}

// --- Curated Preset Palettes ---

const PRESET_PALETTES = {
  'nordic-slate': {
    name: 'Nordic Slate',
    category: 'Light Minimal',
    canvas: '#f8fafc',
    water: '#cbd5e1',
    greenspace: '#e2e8f0',
    roads: '#475569',
    buildings: '#e2e8f0',
    text: '#0f172a'
  },
  'warm-parchment': {
    name: 'Warm Parchment',
    category: 'Editorial Antique',
    canvas: '#fbf9f4',
    water: '#b9d7ea',
    greenspace: '#d9e7cb',
    roads: '#d35400',
    buildings: '#ebe3d5',
    text: '#2c3e50'
  },
  'powder-blue': {
    name: 'Powder Blue',
    category: 'Soft Pastel',
    canvas: '#f2f6fa',
    water: '#b4d4eb',
    greenspace: '#dbe8f2',
    roads: '#15486e',
    buildings: '#cbdfe9',
    text: '#0a2030'
  },
  'cherry-blush': {
    name: 'Cherry Blossom',
    category: 'Soft Pastel',
    canvas: '#fbf4f5',
    water: '#dbb3bb',
    greenspace: '#eddee1',
    roads: '#823545',
    buildings: '#e2cbcf',
    text: '#280b11'
  },
  'synthwave-neon': {
    name: '1980s Neon',
    category: 'Cyberpunk Dark',
    canvas: '#0d021a',
    water: '#16042b',
    greenspace: '#1a0533',
    roads: '#ff007f',
    buildings: '#240a3d',
    text: '#00f0ff'
  },
  'amethyst-night': {
    name: 'Amethyst Luxury',
    category: 'Dark Thematic',
    canvas: '#0c0514',
    water: '#1f0c38',
    greenspace: '#180b2c',
    roads: '#d69eff',
    buildings: '#2d134d',
    text: '#ffffff'
  },
  'oxblood-night': {
    name: 'Oxblood Night',
    category: 'Dark Thematic',
    canvas: '#100305',
    water: '#2b060d',
    greenspace: '#1c0409',
    roads: '#ff7897',
    buildings: '#3b0914',
    text: '#ffffff'
  },
  'metropolis-night': {
    name: 'Metropolis Night',
    category: 'Dark Thematic',
    canvas: '#16181c',
    water: '#0a1524',
    greenspace: '#1a241d',
    roads: '#eb8923',
    buildings: '#262930',
    text: '#ffffff'
  },
  'botanical-sage': {
    name: 'Botanical Sage',
    category: 'Natural Earth',
    canvas: '#f4f8f5',
    water: '#b3d4bb',
    greenspace: '#dbeade',
    roads: '#265e34',
    buildings: '#d5e4d8',
    text: '#081a0e'
  },
  'copper-sepia': {
    name: 'Copperplate Sepia',
    category: 'Archival Print',
    canvas: '#faf7f0',
    water: '#d9cbb4',
    greenspace: '#eee7d8',
    roads: '#61401b',
    buildings: '#e8dec8',
    text: '#1f1304'
  }
};

// --- Single-Hue Monochrome Generator ---

/**
 * Derives a complete 6-token harmonious palette from a single seed color.
 */
function generateMonochromeTokens(seedHex, isDark = false) {
  const rgb = hexToRgb(seedHex);
  const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
  const h = hsl.h;
  const s = clamp(hsl.s, 20, 60);

  if (isDark) {
    return {
      canvas: rgbToHex(hslToRgb(h, s, 6).r, hslToRgb(h, s, 6).g, hslToRgb(h, s, 6).b),
      water: rgbToHex(hslToRgb(h, s, 14).r, hslToRgb(h, s, 14).g, hslToRgb(h, s, 14).b),
      greenspace: rgbToHex(hslToRgb(h, s, 10).r, hslToRgb(h, s, 10).g, hslToRgb(h, s, 10).b),
      roads: rgbToHex(hslToRgb(h, s + 20, 75).r, hslToRgb(h, s + 20, 75).g, hslToRgb(h, s + 20, 75).b),
      buildings: rgbToHex(hslToRgb(h, s, 18).r, hslToRgb(h, s, 18).g, hslToRgb(h, s, 18).b),
      text: '#ffffff'
    };
  } else {
    return {
      canvas: rgbToHex(hslToRgb(h, 15, 97).r, hslToRgb(h, 15, 97).g, hslToRgb(h, 15, 97).b),
      water: rgbToHex(hslToRgb(h, 35, 80).r, hslToRgb(h, 35, 80).g, hslToRgb(h, 35, 80).b),
      greenspace: rgbToHex(hslToRgb(h, 20, 90).r, hslToRgb(h, 20, 90).g, hslToRgb(h, 20, 90).b),
      roads: rgbToHex(hslToRgb(h, 45, 30).r, hslToRgb(h, 45, 30).g, hslToRgb(h, 45, 30).b),
      buildings: rgbToHex(hslToRgb(h, 20, 86).r, hslToRgb(h, 20, 86).g, hslToRgb(h, 20, 86).b),
      text: rgbToHex(hslToRgb(h, 50, 10).r, hslToRgb(h, 50, 10).g, hslToRgb(h, 50, 10).b)
    };
  }
}

// --- Random Harmony Generator ---

function randomBalancedPalette(isDark = false) {
  // STRICT: Always generate strictly according to isDark (never switch modes randomly)
  const baseHue = Math.floor(Math.random() * 360);
  const roadHue = (baseHue + 120 + Math.floor(Math.random() * 60)) % 360; // Triadic / complementary contrast

  if (isDark) {
    return {
      canvas: rgbToHex(hslToRgb(baseHue, 30, 6).r, hslToRgb(baseHue, 30, 6).g, hslToRgb(baseHue, 30, 6).b),
      water: rgbToHex(hslToRgb((baseHue + 30) % 360, 40, 14).r, hslToRgb((baseHue + 30) % 360, 40, 14).g, hslToRgb((baseHue + 30) % 360, 40, 14).b),
      greenspace: rgbToHex(hslToRgb(baseHue, 25, 10).r, hslToRgb(baseHue, 25, 10).g, hslToRgb(baseHue, 25, 10).b),
      roads: rgbToHex(hslToRgb(roadHue, 90, 68).r, hslToRgb(roadHue, 90, 68).g, hslToRgb(roadHue, 90, 68).b),
      buildings: rgbToHex(hslToRgb(baseHue, 25, 16).r, hslToRgb(baseHue, 25, 16).g, hslToRgb(baseHue, 25, 16).b),
      text: '#ffffff'
    };
  } else {
    return {
      canvas: rgbToHex(hslToRgb(baseHue, 15, 97).r, hslToRgb(baseHue, 15, 97).g, hslToRgb(baseHue, 15, 97).b),
      water: rgbToHex(hslToRgb((baseHue + 40) % 360, 40, 78).r, hslToRgb((baseHue + 40) % 360, 40, 78).g, hslToRgb((baseHue + 40) % 360, 40, 78).b),
      greenspace: rgbToHex(hslToRgb((baseHue + 80) % 360, 30, 88).r, hslToRgb((baseHue + 80) % 360, 30, 88).g, hslToRgb((baseHue + 80) % 360, 30, 88).b),
      roads: rgbToHex(hslToRgb(roadHue, 80, 42).r, hslToRgb(roadHue, 80, 42).g, hslToRgb(roadHue, 80, 42).b),
      buildings: rgbToHex(hslToRgb(baseHue, 15, 87).r, hslToRgb(baseHue, 15, 87).g, hslToRgb(baseHue, 15, 87).b),
      text: rgbToHex(hslToRgb(baseHue, 40, 12).r, hslToRgb(baseHue, 40, 12).g, hslToRgb(baseHue, 40, 12).b)
    };
  }
}

// --- Theme Mode Converter (Light <-> Dark) ---

/**
 * Inverts or adapts a 6-token palette between Light and Dark modes,
 * preserving each token's hue character while adapting lightness and saturation
 * for optimal cartographic contrast.
 */
function invertPaletteMode(tokens, targetIsDark) {
  const currentLum = getRelativeLuminance(tokens.canvas);
  const currentlyDark = currentLum < 0.2;

  if (currentlyDark === targetIsDark) {
    return { ...tokens };
  }

  const canvasHsl = rgbToHsl(hexToRgb(tokens.canvas).r, hexToRgb(tokens.canvas).g, hexToRgb(tokens.canvas).b);
  const waterHsl = rgbToHsl(hexToRgb(tokens.water).r, hexToRgb(tokens.water).g, hexToRgb(tokens.water).b);
  const greenHsl = rgbToHsl(hexToRgb(tokens.greenspace).r, hexToRgb(tokens.greenspace).g, hexToRgb(tokens.greenspace).b);
  const roadHsl = rgbToHsl(hexToRgb(tokens.roads).r, hexToRgb(tokens.roads).g, hexToRgb(tokens.roads).b);
  const bldgHsl = rgbToHsl(hexToRgb(tokens.buildings).r, hexToRgb(tokens.buildings).g, hexToRgb(tokens.buildings).b);

  if (targetIsDark) {
    // Switch Light -> Dark
    const darkCanvas = rgbToHex(
      hslToRgb(canvasHsl.h, Math.min(canvasHsl.s, 25), 7).r,
      hslToRgb(canvasHsl.h, Math.min(canvasHsl.s, 25), 7).g,
      hslToRgb(canvasHsl.h, Math.min(canvasHsl.s, 25), 7).b
    );
    const darkWater = rgbToHex(
      hslToRgb(waterHsl.h, Math.min(Math.max(waterHsl.s, 30), 60), 14).r,
      hslToRgb(waterHsl.h, Math.min(Math.max(waterHsl.s, 30), 60), 14).g,
      hslToRgb(waterHsl.h, Math.min(Math.max(waterHsl.s, 30), 60), 14).b
    );
    const darkGreen = rgbToHex(
      hslToRgb(greenHsl.h, Math.min(greenHsl.s, 35), 11).r,
      hslToRgb(greenHsl.h, Math.min(greenHsl.s, 35), 11).g,
      hslToRgb(greenHsl.h, Math.min(greenHsl.s, 35), 11).b
    );
    const darkRoads = rgbToHex(
      hslToRgb(roadHsl.h, Math.max(roadHsl.s, 65), 70).r,
      hslToRgb(roadHsl.h, Math.max(roadHsl.s, 65), 70).g,
      hslToRgb(roadHsl.h, Math.max(roadHsl.s, 65), 70).b
    );
    const darkBldg = rgbToHex(
      hslToRgb(bldgHsl.h, Math.min(bldgHsl.s, 25), 16).r,
      hslToRgb(bldgHsl.h, Math.min(bldgHsl.s, 25), 16).g,
      hslToRgb(bldgHsl.h, Math.min(bldgHsl.s, 25), 16).b
    );

    return {
      canvas: darkCanvas,
      water: darkWater,
      greenspace: darkGreen,
      roads: darkRoads,
      buildings: darkBldg,
      text: '#ffffff'
    };
  } else {
    // Switch Dark -> Light
    const lightCanvas = rgbToHex(
      hslToRgb(canvasHsl.h, Math.min(canvasHsl.s, 20), 97).r,
      hslToRgb(canvasHsl.h, Math.min(canvasHsl.s, 20), 97).g,
      hslToRgb(canvasHsl.h, Math.min(canvasHsl.s, 20), 97).b
    );
    const lightWater = rgbToHex(
      hslToRgb(waterHsl.h, Math.min(Math.max(waterHsl.s, 30), 55), 80).r,
      hslToRgb(waterHsl.h, Math.min(Math.max(waterHsl.s, 30), 55), 80).g,
      hslToRgb(waterHsl.h, Math.min(Math.max(waterHsl.s, 30), 55), 80).b
    );
    const lightGreen = rgbToHex(
      hslToRgb(greenHsl.h, Math.min(greenHsl.s, 35), 90).r,
      hslToRgb(greenHsl.h, Math.min(greenHsl.s, 35), 90).g,
      hslToRgb(greenHsl.h, Math.min(greenHsl.s, 35), 90).b
    );
    const lightRoads = rgbToHex(
      hslToRgb(roadHsl.h, Math.min(Math.max(roadHsl.s, 40), 85), 38).r,
      hslToRgb(roadHsl.h, Math.min(Math.max(roadHsl.s, 40), 85), 38).g,
      hslToRgb(roadHsl.h, Math.min(Math.max(roadHsl.s, 40), 85), 38).b
    );
    const lightBldg = rgbToHex(
      hslToRgb(bldgHsl.h, Math.min(bldgHsl.s, 20), 86).r,
      hslToRgb(bldgHsl.h, Math.min(bldgHsl.s, 20), 86).g,
      hslToRgb(bldgHsl.h, Math.min(bldgHsl.s, 20), 86).b
    );
    const lightText = rgbToHex(
      hslToRgb(canvasHsl.h, Math.min(canvasHsl.s, 40), 12).r,
      hslToRgb(canvasHsl.h, Math.min(canvasHsl.s, 40), 12).g,
      hslToRgb(canvasHsl.h, Math.min(canvasHsl.s, 40), 12).b
    );

    return {
      canvas: lightCanvas,
      water: lightWater,
      greenspace: lightGreen,
      roads: lightRoads,
      buildings: lightBldg,
      text: lightText
    };
  }
}

// --- Auto-Contrast Balancer ---

function autoBalanceContrast(tokens) {
  const balanced = { ...tokens };
  const canvasLum = getRelativeLuminance(balanced.canvas);
  const isDark = canvasLum < 0.2;

  // 1. Ensure Text achieves WCAG AA (>= 4.5:1 against canvas)
  let textRatio = getContrastRatio(balanced.canvas, balanced.text);
  if (textRatio < 4.5) {
    balanced.text = isDark ? '#ffffff' : '#111827';
  }

  // 2. Ensure Water separates from Canvas (>= 1.25:1 fill or distinct step)
  const waterRatio = getContrastRatio(balanced.canvas, balanced.water);
  if (waterRatio < 1.2) {
    balanced.water = isDark 
      ? adjustHsl(balanced.water, { l: +15 }) 
      : adjustHsl(balanced.water, { l: -18 });
  }

  // 3. Ensure Roads pop (>= 3.0:1 against canvas)
  const roadRatio = getContrastRatio(balanced.canvas, balanced.roads);
  if (roadRatio < 3.0) {
    balanced.roads = isDark 
      ? adjustHsl(balanced.roads, { l: +30, s: +20 }) 
      : adjustHsl(balanced.roads, { l: -35, s: +20 });
  }

  return balanced;
}

// Global Export
window.StyleEngine = {
  hexToRgb,
  rgbToHex,
  rgbToHsl,
  hslToRgb,
  adjustHsl,
  getRelativeLuminance,
  getContrastRatio,
  generateThemeConfig,
  compileMapLibreStyle,
  PRESET_PALETTES,
  generateMonochromeTokens,
  randomBalancedPalette,
  invertPaletteMode,
  autoBalanceContrast
};
