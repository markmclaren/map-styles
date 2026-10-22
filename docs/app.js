/**
 * app.js
 * Interactive MapLibre Viewer & Comparison Application
 * Supports Single, Split-screen, and Swipe comparison modes.
 */

// Preset locations [lng, lat, zoom, pitch, bearing]
const PRESETS = {
  bgs: { center: [-1.0772, 52.8797], zoom: 14.5, pitch: 0, bearing: 0, label: 'BGS Keyworth (GeoIndex)' },
  london: { center: [-0.1276, 51.5074], zoom: 12.2, pitch: 0, bearing: 0, label: 'London (UK)' },
  edinburgh: { center: [-3.1883, 55.9533], zoom: 13.5, pitch: 15, bearing: -10, label: 'Edinburgh Castle' },
  lakedistrict: { center: [-3.0500, 54.4500], zoom: 11.0, pitch: 35, bearing: 20, label: 'Lake District (Topo/Relief)' },
  alps: { center: [7.7491, 45.9763], zoom: 11.5, pitch: 45, bearing: 15, label: 'Swiss Alps (Matterhorn)' },
  nyc: { center: [-73.9851, 40.7488], zoom: 13.0, pitch: 20, bearing: -25, label: 'New York City' }
};

// State
let mapPrimary = null;
let mapSecondary = null;
let currentStyleId = 'light-gray';
let currentMode = 'single'; // 'single', 'split', 'swipe'
let currentStyleJson = null;
let isSyncing = false;
let isDraggingSwipe = false;

// DOM Elements
const styleSelect = document.getElementById('styleSelect');
const presetSelect = document.getElementById('presetSelect');
const btnModeSingle = document.getElementById('btnModeSingle');
const btnModeSplit = document.getElementById('btnModeSplit');
const btnModeSwipe = document.getElementById('btnModeSwipe');
const btnInspect = document.getElementById('btnInspect');
const btnDownload = document.getElementById('btnDownload');
const inspectorDrawer = document.getElementById('inspectorDrawer');
const btnCloseInspector = document.getElementById('btnCloseInspector');
const rawJsonCode = document.getElementById('rawJsonCode');
const drawerStyleName = document.getElementById('drawerStyleName');
const mapViewport = document.getElementById('mapViewport');
const mapSecondaryElem = document.getElementById('mapSecondary');
const swipeDivider = document.getElementById('swipeDivider');
const secondaryTag = document.getElementById('secondaryTag');
const hudZoom = document.getElementById('hudZoom');
const hudCoords = document.getElementById('hudCoords');
const hudLayers = document.getElementById('hudLayers');

// Helper to resolve style URLs
function getStyleUrl(styleId) {
  return `dist/${styleId}.json`;
}

// Function to generate UK road sign badges dynamically (TSRGD conventions)
function createUkShield(fillColor, strokeColor) {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 32;
  const ctx = canvas.getContext('2d');
  const r = 6;
  const w = canvas.width - 4;
  const h = canvas.height - 4;
  const x = 2;
  const y = 2;
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
  ctx.fillStyle = fillColor;
  ctx.fill();
  if (strokeColor) {
    ctx.lineWidth = 2;
    ctx.strokeStyle = strokeColor;
    ctx.stroke();
  }
  return ctx.getImageData(0, 0, canvas.width, canvas.height);
}

const UK_SHIELDS_DEF = {
  'shield_uk_motorway': { fill: '#0079C1', stroke: null },
  'shield_uk_primary': { fill: '#00703C', stroke: null },
  'shield_uk_nonprimary': { fill: '#FFFFFF', stroke: '#111111' },
  'shield_uk_junction': { fill: '#111111', stroke: '#FFFFFF' }
};

function addUkShield(map, name) {
  if (!map || map.hasImage(name)) return;
  const s = UK_SHIELDS_DEF[name];
  if (!s) return;
  try {
    map.addImage(name, createUkShield(s.fill, s.stroke), {
      content: [8, 6, 56, 26],
      stretchX: [[12, 52]],
      stretchY: [[8, 24]]
    });
  } catch (err) {
    console.warn(`Could not add image ${name}:`, err);
  }
}

function registerUkShields(map) {
  if (!map) return;
  Object.keys(UK_SHIELDS_DEF).forEach(name => addUkShield(map, name));
}

// Initialize Application
async function init() {
  const initial = PRESETS.london;

  // Initialize Primary Map
  mapPrimary = new maplibregl.Map({
    container: 'mapPrimary',
    style: getStyleUrl(currentStyleId),
    center: initial.center,
    zoom: initial.zoom,
    pitch: initial.pitch,
    bearing: initial.bearing,
    renderWorldCopies: false
  });

  // Navigation Controls
  mapPrimary.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');

  // Initialize Secondary Map (for comparison)
  mapSecondary = new maplibregl.Map({
    container: 'mapSecondary',
    style: getStyleUrl('positron'), // default comparison baseline
    center: initial.center,
    zoom: initial.zoom,
    pitch: initial.pitch,
    bearing: initial.bearing,
    renderWorldCopies: false
  });

  // Synchronize maps
  setupMapSync(mapPrimary, mapSecondary);

  // UK Shields on-demand and on load
  mapPrimary.on('styleimagemissing', (e) => {
    if (UK_SHIELDS_DEF[e.id]) addUkShield(mapPrimary, e.id);
  });
  mapSecondary.on('styleimagemissing', (e) => {
    if (UK_SHIELDS_DEF[e.id]) addUkShield(mapSecondary, e.id);
  });

  // Map event listeners
  mapPrimary.on('move', updateHud);
  mapPrimary.on('load', () => {
    registerUkShields(mapPrimary);
    onMapLoaded();
  });
  mapPrimary.on('style.load', () => {
    registerUkShields(mapPrimary);
    updateHud();
  });
  mapPrimary.on('error', (e) => {
    if (e && e.error) console.error('MapPrimary Error:', e.error);
  });

  mapSecondary.on('load', () => {
    registerUkShields(mapSecondary);
  });
  mapSecondary.on('style.load', () => {
    registerUkShields(mapSecondary);
  });
  mapSecondary.on('error', (e) => {
    if (e && e.error) console.error('MapSecondary Error:', e.error);
  });

  // Setup Event Listeners
  setupEventListeners();

  // Load style JSON for inspection
  loadStyleJson(currentStyleId);
}

function onMapLoaded() {
  updateHud();
}

// Map synchronization between Primary & Secondary
function setupMapSync(map1, map2) {
  function sync(source, target) {
    if (isSyncing) return;
    isSyncing = true;
    target.jumpTo({
      center: source.getCenter(),
      zoom: source.getZoom(),
      bearing: source.getBearing(),
      pitch: source.getPitch()
    });
    isSyncing = false;
  }

  map1.on('move', () => sync(map1, map2));
  map2.on('move', () => sync(map2, map1));
}

// HUD updates
function updateHud() {
  if (!mapPrimary) return;
  const center = mapPrimary.getCenter();
  const zoom = mapPrimary.getZoom();
  hudCoords.textContent = `${center.lng.toFixed(4)}, ${center.lat.toFixed(4)}`;
  hudZoom.textContent = zoom.toFixed(2);
  const layers = mapPrimary.getStyle() ? mapPrimary.getStyle().layers.length : '--';
  hudLayers.textContent = layers;
}

// Event Listeners Setup
function setupEventListeners() {
  // Style switcher
  styleSelect.addEventListener('change', (e) => {
    switchStyle(e.target.value);
  });

  // Presets
  presetSelect.addEventListener('change', (e) => {
    const p = PRESETS[e.target.value];
    if (p) {
      mapPrimary.flyTo({
        center: p.center,
        zoom: p.zoom,
        pitch: p.pitch,
        bearing: p.bearing,
        essential: true,
        duration: 1800
      });
    }
  });

  // Mode toggles
  btnModeSingle.addEventListener('click', () => setViewMode('single'));
  btnModeSplit.addEventListener('click', () => setViewMode('split'));
  btnModeSwipe.addEventListener('click', () => setViewMode('swipe'));

  // Swipe interaction
  setupSwipeInteraction();

  // Inspector
  btnInspect.addEventListener('click', () => {
    inspectorDrawer.classList.toggle('open');
  });

  btnCloseInspector.addEventListener('click', () => {
    inspectorDrawer.classList.remove('open');
  });
}

// Switch Active Converted Style
async function switchStyle(styleId) {
  currentStyleId = styleId;
  const styleUrl = getStyleUrl(styleId);
  
  mapPrimary.setStyle(styleUrl);
  mapPrimary.once('style.load', () => {
    updateHud();
  });

  // In split/swipe comparison mode, set secondary map to reference comparison
  updateSecondaryStyle(styleId);
  loadStyleJson(styleId);
}

// Update secondary map to an appropriate comparison reference
function updateSecondaryStyle(styleId) {
  if (styleId.includes('streetmap') || styleId === 'aa-atlas' || styleId === 'os-roads' || styleId === 'os-landranger') {
    secondaryTag.textContent = 'Ordnance Survey - Roads';
    mapSecondary.setStyle(getStyleUrl('os-roads'));
  } else if (styleId.startsWith('google-maps') || styleId === 'apple-maps' || styleId === 'bing-maps' || styleId === 'mapquest-classic' || styleId === 'here-classic') {
    secondaryTag.textContent = 'OpenFreeMap Liberty';
    mapSecondary.setStyle(getStyleUrl('liberty'));
  } else if (styleId === 'michelin' || styleId === 'rand-mcnally' || styleId === 'swisstopo') {
    secondaryTag.textContent = 'OpenFreeMap Bright';
    mapSecondary.setStyle(getStyleUrl('bright'));
  } else if (styleId === 'stamen-toner' || styleId.includes('dark') || styleId === 'os-zoomstack-night') {
    secondaryTag.textContent = 'OpenFreeMap Dark';
    mapSecondary.setStyle(getStyleUrl('dark'));
  } else if (styleId.includes('osm') || styleId === 'humanitarian') {
    secondaryTag.textContent = 'OpenFreeMap Liberty';
    mapSecondary.setStyle(getStyleUrl('liberty'));
  } else if (styleId.includes('topographic') || styleId.includes('relief') || styleId.includes('outdoor') || styleId === 'natgeo') {
    secondaryTag.textContent = 'OpenFreeMap Shaded Liberty';
    mapSecondary.setStyle(getStyleUrl('liberty'));
  } else if (styleId === 'eighties-neon' || styleId === 'monochrome-purple' || styleId === 'monochrome-crimson') {
    secondaryTag.textContent = 'OpenFreeMap Dark';
    mapSecondary.setStyle(getStyleUrl('dark'));
  } else if (styleId === 'eighties-pastel') {
    secondaryTag.textContent = 'OpenFreeMap Bright';
    mapSecondary.setStyle(getStyleUrl('bright'));
  } else if (styleId.startsWith('monochrome')) {
    secondaryTag.textContent = 'OpenFreeMap Positron';
    mapSecondary.setStyle(getStyleUrl('positron'));
  } else {
    secondaryTag.textContent = 'OpenFreeMap Positron';
    mapSecondary.setStyle(getStyleUrl('positron'));
  }
}

// View Mode Switching
function setViewMode(mode) {
  currentMode = mode;
  [btnModeSingle, btnModeSplit, btnModeSwipe].forEach(b => b.classList.remove('active'));

  mapViewport.classList.remove('mode-split', 'mode-swipe');
  mapSecondaryElem.classList.add('comparison-hidden');
  swipeDivider.classList.add('comparison-hidden');

  if (mode === 'single') {
    btnModeSingle.classList.add('active');
  } else if (mode === 'split') {
    btnModeSplit.classList.add('active');
    mapViewport.classList.add('mode-split');
    mapSecondaryElem.classList.remove('comparison-hidden');
    mapPrimary.resize();
    mapSecondary.resize();
  } else if (mode === 'swipe') {
    btnModeSwipe.classList.add('active');
    mapViewport.classList.add('mode-swipe');
    mapSecondaryElem.classList.remove('comparison-hidden');
    swipeDivider.classList.remove('comparison-hidden');
    setSwipePosition(window.innerWidth / 2);
    mapPrimary.resize();
    mapSecondary.resize();
  }
}

// Swipe Slider Handling
function setupSwipeInteraction() {
  function onPointerMove(e) {
    if (!isDraggingSwipe) return;
    setSwipePosition(e.clientX);
  }

  function onPointerUp() {
    isDraggingSwipe = false;
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
  }

  swipeDivider.addEventListener('pointerdown', (e) => {
    isDraggingSwipe = true;
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
  });
}

function setSwipePosition(x) {
  const width = window.innerWidth;
  const clampedX = Math.max(50, Math.min(width - 50, x));
  const percent = (clampedX / width) * 100;
  swipeDivider.style.left = `${percent}%`;
  mapSecondaryElem.style.clipPath = `polygon(${percent}% 0, 100% 0, 100% 100%, ${percent}% 100%)`;
}

// Load and display style JSON in Inspector
async function loadStyleJson(styleId) {
  try {
    const res = await fetch(getStyleUrl(styleId));
    const data = await res.json();
    currentStyleJson = data;

    drawerStyleName.textContent = data.name || styleId;
    rawJsonCode.textContent = JSON.stringify(data, null, 2);

    // Update download button
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    btnDownload.href = URL.createObjectURL(blob);
    btnDownload.download = `${styleId}.json`;
  } catch (err) {
    console.error('Failed to load style JSON for inspection:', err);
  }
}

// Launch
window.addEventListener('DOMContentLoaded', init);
