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
let currentMode = 'light'; // 'light' | 'dark'
let activeHarmony = 'triadic'; // 'triadic' | 'complementary' | 'split-complementary' | 'analogous' | 'tetradic' | 'monochrome' | 'random'

// Slot-Machine "HOLD" state: true prevents the token from spinning during shuffle
let heldTokens = {
  canvas: false,
  water: false,
  greenspace: false,
  roads: false,
  buildings: false,
  text: false
};

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
const shuffleLabel = document.getElementById('shuffleLabel');
const btnAutoContrast = document.getElementById('btnAutoContrast');
const btnMonoLock = document.getElementById('btnMonoLock');
const btnClearHolds = document.getElementById('btnClearHolds');
const selectHarmony = document.getElementById('selectHarmony');
const harmonyBadge = document.getElementById('harmonyBadge');
const btnHarmonize = document.getElementById('btnHarmonize');
const btnModeLight = document.getElementById('btnModeLight');
const btnModeDark = document.getElementById('btnModeDark');
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

  // 2. Fetch base template (checks window.BASE_TEMPLATE first for instant & offline/file:// support)
  if (window.BASE_TEMPLATE) {
    baseTemplate = window.BASE_TEMPLATE;
  } else {
    try {
      const res = await fetch('dist/bright.json');
      if (res.ok) {
        baseTemplate = await res.json();
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err) {
      console.warn('Local template fetch failed, attempting remote fallback:', err);
      try {
        const resRemote = await fetch('https://tiles.openfreemap.org/styles/bright');
        baseTemplate = await resRemote.json();
      } catch (err2) {
        console.error('All base template sources failed:', err2);
        showToast('Failed to load map template');
      }
    }
  }

  // 3. Compile initial style
  if (baseTemplate) {
    const theme = StyleEngine.generateThemeConfig(tokens);
    currentStyle = StyleEngine.compileMapLibreStyle(baseTemplate, theme);
  }

  // 4. Initialize MapLibre
  const initialLoc = PRESETS.london;
  if (currentStyle) {
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
      if (btnProjMercator) btnProjMercator.classList.toggle('active', p === 'mercator');
      if (btnProjGlobe) btnProjGlobe.classList.toggle('active', p === 'globe');
    });
  }

  // 5. Setup UI & Event Listeners (ALWAYS execute so UI remains interactive)
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
  }, 120);
}

// Compile and update MapLibre in memory
function applyCompiledStyle() {
  if (!baseTemplate) return;

  const theme = StyleEngine.generateThemeConfig(tokens);
  currentStyle = StyleEngine.compileMapLibreStyle(baseTemplate, theme);

  if (map) {
    map.setStyle(currentStyle);
    if (currentProjection === 'globe') {
      map.once('style.load', () => {
        map.setProjection({ type: 'globe' });
        updateHud();
      });
    } else {
      map.once('style.load', updateHud);
    }
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

// Update mode toggles, contrast scores, and inspector drawer
function updateUiState() {
  const canvasLum = StyleEngine.getRelativeLuminance(tokens.canvas);
  const isDark = canvasLum < 0.2;
  currentMode = isDark ? 'dark' : 'light';

  // Synchronize explicit Light / Dark mode toggle buttons
  if (btnModeLight) btnModeLight.classList.toggle('active', !isDark);
  if (btnModeDark) btnModeDark.classList.toggle('active', isDark);

  // Backward compatibility with legacy badge if present
  const badgeMode = document.getElementById('badgeMode');
  if (badgeMode) {
    badgeMode.textContent = isDark ? 'Dark Mode' : 'Light Mode';
    badgeMode.className = `badge-mode ${isDark ? 'badge-dark' : 'badge-light'}`;
  }

  // Contrast Calculation (Text vs Canvas)
  const ratio = StyleEngine.getContrastRatio(tokens.canvas, tokens.text);
  if (contrastValue) {
    contrastValue.textContent = `${ratio.toFixed(1)}:1 (${ratio >= 7.0 ? 'AAA' : (ratio >= 4.5 ? 'AA' : 'Fail')})`;
  }

  if (contrastPill) {
    contrastPill.className = 'contrast-pill';
    if (ratio >= 7.0) {
      contrastPill.classList.add('pass-aaa');
    } else if (ratio >= 4.5) {
      contrastPill.classList.add('pass-aa');
    } else {
      contrastPill.classList.add('fail');
    }
  }

  // Update active pill highlight
  document.querySelectorAll('.preset-pill').forEach(pill => {
    const pId = pill.dataset.preset;
    const p = StyleEngine.PRESET_PALETTES[pId];
    if (p) {
      const match = Object.keys(tokens).every(k => tokens[k] && p[k] && tokens[k].toLowerCase() === p[k].toLowerCase());
      pill.classList.toggle('active', match);
    }
  });

  // Re-render tonal ladders for all 6 tokens
  renderTonalLadders();

  // Synchronize slot machine HOLD states and active harmony badge
  updateHoldUi();
  updateHarmonyBadge();
}

// Toggle slot-machine HOLD for a token
function toggleHold(tokenKey) {
  if (heldTokens[tokenKey] === undefined) return;
  heldTokens[tokenKey] = !heldTokens[tokenKey];
  updateHoldUi();
  const isHeld = heldTokens[tokenKey];
  showToast(isHeld ? `🔒 Held ${tokenKey} (locked from shuffle)` : `Released hold on ${tokenKey}`);
}

// Synchronize HOLD button visuals and card indicators
function updateHoldUi() {
  const count = Object.values(heldTokens).filter(Boolean).length;

  // Update hold buttons on all cards
  document.querySelectorAll('.btn-hold').forEach(btn => {
    const key = btn.dataset.token;
    const isHeld = !!heldTokens[key];
    btn.classList.toggle('is-held', isHeld);
    const textSpan = btn.querySelector('.hold-text');
    if (textSpan) textSpan.textContent = isHeld ? 'HELD' : 'HOLD';
    btn.title = isHeld ? 'Locked: Color is preserved during shuffle (Click to release)' : 'Hold: Lock color during shuffle';

    // Highlight parent card
    const card = document.getElementById(`card${key.charAt(0).toUpperCase() + key.slice(1)}`);
    if (card) card.classList.toggle('token-held', isHeld);
  });

  // Update Shuffle button label
  if (shuffleLabel) {
    if (count === 6) {
      shuffleLabel.textContent = 'All Held 🔒';
    } else if (count > 0) {
      shuffleLabel.textContent = `Shuffle 🎰 (${count} Held)`;
    } else {
      shuffleLabel.textContent = 'Shuffle 🎰';
    }
  }

  // Update Release Holds button
  if (btnClearHolds) {
    btnClearHolds.style.display = count > 0 ? 'flex' : 'none';
    const span = btnClearHolds.querySelector('span');
    if (span) span.textContent = `Release Holds (${count})`;
  }
}

// Release all active holds with one click
function clearAllHolds() {
  Object.keys(heldTokens).forEach(k => { heldTokens[k] = false; });
  updateHoldUi();
  showToast('All color holds released');
}

// Update the harmony pill display
function updateHarmonyBadge() {
  if (!harmonyBadge) return;
  const map = {
    triadic: 'Triadic 120°',
    complementary: 'Contrast 180°',
    'split-complementary': 'Split 150°/210°',
    analogous: 'Analogous 30°',
    tetradic: 'Tetradic Dual',
    monochrome: 'Single Hue',
    random: 'Surprise'
  };
  harmonyBadge.textContent = map[activeHarmony] || activeHarmony;
}

// Trigger reel spin animation on unheld cards
function triggerSlotSpinAnimation() {
  Object.keys(TOKEN_INPUTS).forEach(key => {
    if (!heldTokens[key]) {
      const card = document.getElementById(`card${key.charAt(0).toUpperCase() + key.slice(1)}`);
      if (card) {
        card.classList.remove('slot-spinning');
        void card.offsetWidth; // Force CSS reflow
        card.classList.add('slot-spinning');
        setTimeout(() => card.classList.remove('slot-spinning'), 360);
      }
    }
  });
}

// Execute harmonious shuffle honoring held colors
function executeHarmoniousShuffle(harmonyChoice) {
  const heldCount = Object.values(heldTokens).filter(Boolean).length;
  if (heldCount === 6) {
    showToast('All 6 colors are held! Release at least one hold to shuffle.');
    return;
  }

  const isDark = (currentMode === 'dark');
  const chosenHarmony = harmonyChoice || activeHarmony;

  triggerSlotSpinAnimation();

  if (isMonochromeLocked || chosenHarmony === 'monochrome') {
    tokens = StyleEngine.generateMonochromeTokens(tokens.roads || tokens.canvas, isDark);
  } else {
    tokens = StyleEngine.generateHarmoniousPalette({
      isDark,
      harmony: chosenHarmony,
      currentTokens: tokens,
      held: heldTokens
    });
  }

  syncTokenInputs();
  updateUiState();
  applyCompiledStyle();

  const msg = heldCount > 0 
    ? `Shuffled (${heldCount} held, ${chosenHarmony})` 
    : `Generated ${chosenHarmony} harmony (${isDark ? 'Dark' : 'Light'})`;
  showToast(msg);
}

// Render interactive 5-chip tonal ladder for each token
function renderTonalLadders() {
  const deltas = [-16, -8, 0, 8, 16];
  Object.keys(TOKEN_INPUTS).forEach(key => {
    const id = `ladder${key.charAt(0).toUpperCase() + key.slice(1)}`;
    const ladder = document.getElementById(id);
    if (!ladder) return;

    ladder.innerHTML = '';
    const baseColor = tokens[key];

    deltas.forEach(delta => {
      const chipColor = StyleEngine.adjustHsl(baseColor, { l: delta });
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = `tonal-chip ${delta === 0 ? 'active' : ''}`;
      chip.style.backgroundColor = chipColor;
      chip.title = `${delta === 0 ? 'Current' : (delta > 0 ? `+${delta}% Lighter` : `${delta}% Darker`)} (${chipColor})`;

      chip.addEventListener('click', () => {
        onTokenChanged(key, chipColor);
        if (TOKEN_INPUTS[key]) {
          TOKEN_INPUTS[key].picker.value = chipColor;
          TOKEN_INPUTS[key].text.value = chipColor;
        }
      });

      ladder.appendChild(chip);
    });
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

// Switch theme mode between Light and Dark explicitly
function setThemeMode(targetMode) {
  currentMode = targetMode;
  const isDark = (targetMode === 'dark');

  // Adapt current palette to the chosen mode preserving user's hues and design intent
  tokens = StyleEngine.invertPaletteMode(tokens, isDark);
  tokens = StyleEngine.autoBalanceContrast(tokens);

  syncTokenInputs();
  updateUiState();
  applyCompiledStyle();
  showToast(`Switched to ${isDark ? 'Dark' : 'Light'} Mode`);
}

// Event Listeners
function setupEventListeners() {
  // Theme Mode toggles (Light / Dark)
  btnModeLight.addEventListener('click', () => {
    if (currentMode === 'light') return;
    setThemeMode('light');
  });

  btnModeDark.addEventListener('click', () => {
    if (currentMode === 'dark') return;
    setThemeMode('dark');
  });

  // Lightness nudge steppers (Darker / Lighter buttons)
  document.querySelectorAll('.btn-tone-step').forEach(btn => {
    btn.addEventListener('click', () => {
      const tokenKey = btn.dataset.token;
      const delta = parseInt(btn.dataset.delta, 10) || 0;
      if (!tokens[tokenKey]) return;

      const newColor = StyleEngine.adjustHsl(tokens[tokenKey], { l: delta });
      onTokenChanged(tokenKey, newColor);
      if (TOKEN_INPUTS[tokenKey]) {
        TOKEN_INPUTS[tokenKey].picker.value = newColor;
        TOKEN_INPUTS[tokenKey].text.value = newColor;
      }
    });
  });

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

  // Slot-Machine HOLD Buttons (Clicking toggles hold on that color reel)
  document.querySelectorAll('.btn-hold').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const tokenKey = btn.dataset.token;
      toggleHold(tokenKey);
    });
  });

  // Color Theory Harmony Selector
  if (selectHarmony) {
    selectHarmony.addEventListener('change', (e) => {
      activeHarmony = e.target.value;
      updateHarmonyBadge();
      showToast(`Selected ${activeHarmony.replace('-', ' ')} harmony`);
    });
  }

  // Harmonize Button (Applies active harmony without randomizing seed)
  if (btnHarmonize) {
    btnHarmonize.addEventListener('click', () => {
      executeHarmoniousShuffle(activeHarmony);
    });
  }

  // Release All Holds Button
  if (btnClearHolds) {
    btnClearHolds.addEventListener('click', () => {
      clearAllHolds();
    });
  }

  // Shuffle button (Honors active Light/Dark mode, color harmony, and HOLD locks)
  btnShuffle.addEventListener('click', () => {
    executeHarmoniousShuffle(activeHarmony);
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
      const isDark = (currentMode === 'dark');
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

// Launch safely regardless of document ready state
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
