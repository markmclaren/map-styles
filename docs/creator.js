/**
 * creator.js
 * Controller for the Minimalist MapLibre Style Studio
 */

// Preset locations [lng, lat, zoom, pitch, bearing]
const PRESETS = {
  london: { center: [-0.1276, 51.5074], zoom: 12.2, pitch: 0, bearing: 0, label: 'London (UK)' },
  tokyo: { center: [139.6917, 35.6895], zoom: 12.5, pitch: 15, bearing: -10, label: 'Tokyo (Japan)' },
  nyc: { center: [-73.9851, 40.7488], zoom: 13.0, pitch: 20, bearing: -25, label: 'New York City' },
  paris: { center: [2.3522, 48.8566], zoom: 12.8, pitch: 0, bearing: 0, label: 'Paris (France)' },
  alps: { center: [7.7491, 45.9763], zoom: 11.5, pitch: 45, bearing: 15, label: 'Swiss Alps (Matterhorn)' },
  global: { center: [0, 20], zoom: 1.5, pitch: 0, bearing: 0, label: 'Global (Orbital 3D)' }
};

// Application State
let map = null;
let baseTemplate = null;
let currentStyle = null;
let currentProjection = 'mercator';
let compileTimeout = null;
let isMonochromeLocked = false;

// Active 6 Design Tokens (defaults to Nordic Slate)
let tokens = {
  canvas: '#f8fafc',
  water: '#cbd5e1',
  greenspace: '#e2e8f0',
  roads: '#475569',
  buildings: '#e2e8f0',
  text: '#0f172a'
};

// DOM References
const locationSelect = document.getElementById('locationSelect');
const btnProjMercator = document.getElementById('btnProjMercator');
const btnProjGlobe = document.getElementById('btnProjGlobe');
const btnShare = document.getElementById('btnShare');
const btnInspect = document.getElementById('btnInspect');
const btnDownload = document.getElementById('btnDownload');
const btnShuffle = document.getElementById('btnShuffle');
const btnAutoContrast = document.getElementById('btnAutoContrast');
const btnMonoLock = document.getElementById('btnMonoLock');
const badgeMode = document.getElementById('badgeMode');
const contrastPill = document.getElementById('contrastPill');
const contrastValue = document.getElementById('contrastValue');
const presetPillsContainer = document.getElementById('presetPillsContainer');
const inspectorDrawer = document.getElementById('inspectorDrawer');
const btnCloseInspector = document.getElementById('btnCloseInspector');
const btnCopyJson = document.getElementById('btnCopyJson');
const rawJsonCode = document.getElementById('rawJsonCode');
const studioToast = document.getElementById('studioToast');
const hudCoords = document.getElementById('hudCoords');
const hudZoom = document.getElementById('hudZoom');
const hudLayers = document.getElementById('hudLayers');

// Token Element Maps
const TOKEN_INPUTS = {
  canvas: { picker: document.getElementById('pickerCanvas'), text: document.getElementById('textCanvas') },
  water: { picker: document.getElementById('pickerWater'), text: document.getElementById('textWater') },
  greenspace: { picker: document.getElementById('pickerGreenspace'), text: document.getElementById('textGreenspace') },
  roads: { picker: document.getElementById('pickerRoads'), text: document.getElementById('textRoads') },
  buildings: { picker: document.getElementById('pickerBuildings'), text: document.getElementById('textBuildings') },
  text: { picker: document.getElementById('pickerText'), text: document.getElementById('textText') }
};

// Initialize Application
async function init() {
  // 1. Read URL params / hash if available
  loadTokensFromUrl();

  // 2. Fetch base template
  try {
    const res = await fetch('dist/bright.json');
    baseTemplate = await res.json();
  } catch (err) {
    console.error('Failed to load base template:', err);
    showToast('Failed to load base MapLibre template');
    return;
  }

  // 3. Compile initial style
  const theme = StyleEngine.generateThemeConfig(tokens);
  currentStyle = StyleEngine.compileMapLibreStyle(baseTemplate, theme);

  // 4. Initialize MapLibre
  const initialLoc = PRESETS.london;
  map = new maplibregl.Map({
    container: 'map',
    style: currentStyle,
    center: initialLoc.center,
    zoom: initialLoc.zoom,
    pitch: initialLoc.pitch,
    bearing: initialLoc.bearing,
    renderWorldCopies: false
  });

  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
  if (maplibregl.GlobeControl) {
    map.addControl(new maplibregl.GlobeControl(), 'top-right');
  }

  map.on('move', updateHud);
  map.on('load', updateHud);
  map.on('projectionchange', (e) => {
    const p = (e.newProjection && typeof e.newProjection === 'object' ? e.newProjection.type : e.newProjection) || 'mercator';
    currentProjection = p;
    btnProjMercator.classList.toggle('active', p === 'mercator');
    btnProjGlobe.classList.toggle('active', p === 'globe');
  });

  // 5. Setup UI & Event Listeners
  setupTokenBindings();
  renderPresetPills();
  setupEventListeners();
  updateUiState();
}

// Setup input listeners for the 6 color pickers
function setupTokenBindings() {
  Object.keys(TOKEN_INPUTS).forEach(key => {
    const { picker, text } = TOKEN_INPUTS[key];

    picker.addEventListener('input', (e) => {
      text.value = e.target.value.toLowerCase();
      onTokenChanged(key, e.target.value);
    });

    text.addEventListener('input', (e) => {
      let val = e.target.value.trim();
      if (!val.startsWith('#')) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        picker.value = val;
        onTokenChanged(key, val);
      }
    });
  });
}

// Debounced style compilation when a token changes
function onTokenChanged(changedKey, value) {
  tokens[changedKey] = value;

  // Handle single-hue monochrome lock
  if (isMonochromeLocked && (changedKey === 'roads' || changedKey === 'canvas')) {
    const isDark = StyleEngine.getRelativeLuminance(tokens.canvas) < 0.2;
    tokens = StyleEngine.generateMonochromeTokens(value, isDark);
    syncTokenInputs();
  }

  updateUiState();

  clearTimeout(compileTimeout);
  compileTimeout = setTimeout(() => {
    applyCompiledStyle();
  }, 40);
}

// Compile and update MapLibre in memory
function applyCompiledStyle() {
  if (!baseTemplate) return;

  const theme = StyleEngine.generateThemeConfig(tokens);
  currentStyle = StyleEngine.compileMapLibreStyle(baseTemplate, theme);

  map.setStyle(currentStyle);
  if (currentProjection === 'globe') {
    map.once('style.load', () => {
      map.setProjection({ type: 'globe' });
      updateHud();
    });
  } else {
    map.once('style.load', updateHud);
  }

  updateInspectorJson();
  saveTokensToUrl();
}

// Synchronize DOM inputs with tokens state
function syncTokenInputs() {
  Object.keys(TOKEN_INPUTS).forEach(key => {
    const { picker, text } = TOKEN_INPUTS[key];
    picker.value = tokens[key];
    text.value = tokens[key];
  });
}

// Update badges, contrast scores, and inspector drawer
function updateUiState() {
  const canvasLum = StyleEngine.getRelativeLuminance(tokens.canvas);
  const isDark = canvasLum < 0.2;

  // Mode Badge
  badgeMode.textContent = isDark ? 'Dark Mode' : 'Light Mode';
  badgeMode.className = `badge-mode ${isDark ? 'badge-dark' : 'badge-light'}`;

  // Contrast Calculation (Text vs Canvas)
  const ratio = StyleEngine.getContrastRatio(tokens.canvas, tokens.text);
  contrastValue.textContent = `${ratio.toFixed(1)}:1 (${ratio >= 7.0 ? 'AAA' : (ratio >= 4.5 ? 'AA' : 'Fail')})`;

  contrastPill.className = 'contrast-pill';
  if (ratio >= 7.0) {
    contrastPill.classList.add('pass-aaa');
  } else if (ratio >= 4.5) {
    contrastPill.classList.add('pass-aa');
  } else {
    contrastPill.classList.add('fail');
  }

  // Update active pill highlight
  document.querySelectorAll('.preset-pill').forEach(pill => {
    const pId = pill.dataset.preset;
    const p = StyleEngine.PRESET_PALETTES[pId];
    if (p) {
      const match = Object.keys(tokens).every(k => tokens[k].toLowerCase() === p[k].toLowerCase());
      pill.classList.toggle('active', match);
    }
  });
}

// Render the curated preset pills
function renderPresetPills() {
  presetPillsContainer.innerHTML = '';
  Object.keys(StyleEngine.PRESET_PALETTES).forEach(pId => {
    const p = StyleEngine.PRESET_PALETTES[pId];
    const pill = document.createElement('button');
    pill.className = 'preset-pill';
    pill.dataset.preset = pId;
    pill.innerHTML = `
      <span class="preset-swatch-dots">
        <span class="preset-dot" style="background:${p.canvas}"></span>
        <span class="preset-dot" style="background:${p.water}"></span>
        <span class="preset-dot" style="background:${p.roads}"></span>
      </span>
      <span>${p.name}</span>
    `;

    pill.addEventListener('click', () => {
      tokens = { ...p };
      syncTokenInputs();
      updateUiState();
      applyCompiledStyle();
      showToast(`Applied ${p.name}`);
    });

    presetPillsContainer.appendChild(pill);
  });
}

// HUD updates
function updateHud() {
  if (!map) return;
  const center = map.getCenter();
  const zoom = map.getZoom();
  hudCoords.textContent = `${center.lng.toFixed(4)}, ${center.lat.toFixed(4)}`;
  hudZoom.textContent = zoom.toFixed(2);
  const layers = map.getStyle() ? map.getStyle().layers.length : '--';
  hudLayers.textContent = layers;
}

// Update JSON code preview in Inspector
function updateInspectorJson() {
  if (currentStyle) {
    rawJsonCode.textContent = JSON.stringify(currentStyle, null, 2);
  }
}

// Event Listeners
function setupEventListeners() {
  // Location select
  locationSelect.addEventListener('change', (e) => {
    const p = PRESETS[e.target.value];
    if (p) {
      map.flyTo({
        center: p.center,
        zoom: p.zoom,
        pitch: p.pitch,
        bearing: p.bearing,
        essential: true,
        duration: 1800
      });
    }
  });

  // Projection toggles
  btnProjMercator.addEventListener('click', () => {
    currentProjection = 'mercator';
    btnProjMercator.classList.add('active');
    btnProjGlobe.classList.remove('active');
    map.setProjection({ type: 'mercator' });
  });

  btnProjGlobe.addEventListener('click', () => {
    currentProjection = 'globe';
    btnProjGlobe.classList.add('active');
    btnProjMercator.classList.remove('active');
    map.setProjection({ type: 'globe' });
  });

  // Shuffle button
  btnShuffle.addEventListener('click', () => {
    const isDark = StyleEngine.getRelativeLuminance(tokens.canvas) < 0.2;
    tokens = StyleEngine.randomBalancedPalette(isDark);
    syncTokenInputs();
    updateUiState();
    applyCompiledStyle();
    showToast('Generated random balanced palette');
  });

  // Auto-Contrast button
  btnAutoContrast.addEventListener('click', () => {
    tokens = StyleEngine.autoBalanceContrast(tokens);
    syncTokenInputs();
    updateUiState();
    applyCompiledStyle();
    showToast('Auto-tuned for WCAG AA compliance');
  });

  // Monochrome Lock
  btnMonoLock.addEventListener('click', () => {
    isMonochromeLocked = !isMonochromeLocked;
    btnMonoLock.classList.toggle('active', isMonochromeLocked);
    if (isMonochromeLocked) {
      const isDark = StyleEngine.getRelativeLuminance(tokens.canvas) < 0.2;
      tokens = StyleEngine.generateMonochromeTokens(tokens.roads || tokens.canvas, isDark);
      syncTokenInputs();
      updateUiState();
      applyCompiledStyle();
      showToast('Monochrome lock enabled');
    } else {
      showToast('Monochrome lock disabled');
    }
  });

  // Share button
  btnShare.addEventListener('click', () => {
    saveTokensToUrl();
    navigator.clipboard.writeText(window.location.href).then(() => {
      showToast('Shareable URL copied to clipboard!');
    }).catch(() => {
      showToast('URL updated in address bar');
    });
  });

  // Inspector Drawer
  btnInspect.addEventListener('click', () => {
    inspectorDrawer.classList.toggle('open');
    updateInspectorJson();
  });

  btnCloseInspector.addEventListener('click', () => {
    inspectorDrawer.classList.remove('open');
  });

  // Copy JSON
  btnCopyJson.addEventListener('click', () => {
    if (!currentStyle) return;
    navigator.clipboard.writeText(JSON.stringify(currentStyle, null, 2)).then(() => {
      showToast('Style JSON copied to clipboard!');
    });
  });

  // Download Style JSON
  btnDownload.addEventListener('click', () => {
    if (!currentStyle) return;
    const blob = new Blob([JSON.stringify(currentStyle, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `custom-map-style.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Downloaded custom-map-style.json');
  });
}

// URL State Encoding/Decoding
function saveTokensToUrl() {
  const params = new URLSearchParams();
  params.set('c', tokens.canvas.replace('#', ''));
  params.set('w', tokens.water.replace('#', ''));
  params.set('g', tokens.greenspace.replace('#', ''));
  params.set('r', tokens.roads.replace('#', ''));
  params.set('b', tokens.buildings.replace('#', ''));
  params.set('t', tokens.text.replace('#', ''));
  history.replaceState(null, '', `#${params.toString()}`);
}

function loadTokensFromUrl() {
  if (!window.location.hash || window.location.hash.length < 5) return;
  try {
    const params = new URLSearchParams(window.location.hash.substring(1));
    if (params.has('c')) tokens.canvas = '#' + params.get('c');
    if (params.has('w')) tokens.water = '#' + params.get('w');
    if (params.has('g')) tokens.greenspace = '#' + params.get('g');
    if (params.has('r')) tokens.roads = '#' + params.get('r');
    if (params.has('b')) tokens.buildings = '#' + params.get('b');
    if (params.has('t')) tokens.text = '#' + params.get('t');
  } catch (err) {
    console.warn('Could not parse tokens from URL:', err);
  }
}

// Toast notification helper
function showToast(msg) {
  studioToast.textContent = msg;
  studioToast.classList.add('show');
  setTimeout(() => {
    studioToast.classList.remove('show');
  }, 2400);
}

// Launch
window.addEventListener('DOMContentLoaded', init);
