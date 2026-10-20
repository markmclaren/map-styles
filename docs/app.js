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
    bearing: initial.bearing
  });

  // Navigation Controls
  mapPrimary.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');

  // Initialize Secondary Map (for comparison)
  mapSecondary = new maplibregl.Map({
    container: 'mapSecondary',
    style: 'https://tiles.openfreemap.org/styles/bright', // default comparison baseline
    center: initial.center,
    zoom: initial.zoom,
    pitch: initial.pitch,
    bearing: initial.bearing
  });

  // Synchronize maps
  setupMapSync(mapPrimary, mapSecondary);

  // Map event listeners
  mapPrimary.on('move', updateHud);
  mapPrimary.on('load', onMapLoaded);

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
  if (styleId.includes('osm')) {
    secondaryTag.textContent = 'OpenFreeMap Standard Liberty';
    mapSecondary.setStyle('https://tiles.openfreemap.org/styles/liberty');
  } else if (styleId.includes('dark')) {
    secondaryTag.textContent = 'OpenFreeMap Standard Dark';
    mapSecondary.setStyle('https://tiles.openfreemap.org/styles/dark');
  } else if (styleId.includes('topographic') || styleId.includes('relief') || styleId.includes('outdoor')) {
    secondaryTag.textContent = 'OpenFreeMap Shaded Liberty';
    mapSecondary.setStyle('https://tiles.openfreemap.org/styles/liberty');
  } else if (styleId.includes('roads')) {
    secondaryTag.textContent = 'OpenFreeMap Standard Bright';
    mapSecondary.setStyle('https://tiles.openfreemap.org/styles/bright');
  } else {
    secondaryTag.textContent = 'OpenFreeMap Standard Positron';
    mapSecondary.setStyle('https://tiles.openfreemap.org/styles/positron');
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
