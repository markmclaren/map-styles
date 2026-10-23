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
const btnPrevHarmony = document.getElementById('btnPrevHarmony') || document.getElementById('btnRotateCcw');
const btnNextHarmony = document.getElementById('btnNextHarmony') || document.getElementById('btnRotateCw');
const btnWheelRotateCcw = document.getElementById('btnWheelRotateCcw');
const btnWheelRotateCw = document.getElementById('btnWheelRotateCw');
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

// Slot cabinet
const reelsEl = document.getElementById('reels');
const slotCabinet = document.getElementById('slotCabinet');
const leverEl = document.getElementById('lever');
const leverArm = document.getElementById('leverArm');
const marqueeStars = document.getElementById('marqueeStars');
const marqueeText = document.getElementById('marqueeText');
const marqueeScreen = document.getElementById('marqueeScreen');
const btnSound = document.getElementById('btnSound');

// Colour wheel state
let selectedWheelToken = 'roads';
let anchorToken = 'roads';
let draggingWheelPin = null;

const TOKEN_ORDER = ['canvas', 'water', 'greenspace', 'roads', 'buildings', 'text'];

// Token Metadata
const TOKEN_META = {
  canvas: { name: 'Canvas', short: 'Land', icon: '🏞️', desc: 'Base terrain' },
  water: { name: 'Water', short: 'Water', icon: '🌊', desc: 'Oceans & rivers' },
  greenspace: { name: 'Greenspace', short: 'Parks', icon: '🌲', desc: 'Parks & nature' },
  roads: { name: 'Roads', short: 'Roads', icon: '🚗', desc: 'Highway spine' },
  buildings: { name: 'Buildings', short: 'Blocks', icon: '🏢', desc: 'Urban blocks' },
  text: { name: 'Labels', short: 'Labels', icon: '🔤', desc: 'City text' }
};

// Colour Wheel DOM References
const colorWheelCanvas = document.getElementById('colorWheelCanvas');
const colorWheelSvg = document.getElementById('colorWheelSvg');


// Populated by buildReels(): { picker, text } per token
const TOKEN_INPUTS = {};

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
  if (currentStyle && typeof maplibregl !== 'undefined') {
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
  buildReels();
  buildPopoverSwatches();
  setupTokenBindings();
  setupLever();
  renderPresetPills();
  renderColorWheelCanvas();
  setupColorWheelInteractions();
  setupEventListeners();
  selectWheelToken('roads');
  updateUiState();
  updateInspectorJson();
}

// Setup input listeners for the 6 colour pickers / hex fields
function setupTokenBindings() {
  Object.keys(TOKEN_INPUTS).forEach(key => {
    const { picker, text } = TOKEN_INPUTS[key];
    text.addEventListener('input', (e) => {
      let val = e.target.value.trim();
      if (!val.startsWith('#')) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        picker.value = val.toLowerCase();
        onTokenChanged(key, val.toLowerCase());
      }
    });
    text.addEventListener('focus', () => text.select());
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

// Synchronize DOM inputs with tokens state
function syncTokenInputs() {
  Object.keys(TOKEN_INPUTS).forEach(key => {
    const { picker, text } = TOKEN_INPUTS[key];
    picker.value = tokens[key];
    text.value = tokens[key];
  });
}

// Update mode toggles, contrast scores, reels and wheel
function updateUiState() {
  const canvasLum = StyleEngine.getRelativeLuminance(tokens.canvas);
  const isDark = canvasLum < 0.2;
  currentMode = isDark ? 'dark' : 'light';

  if (btnModeLight) btnModeLight.classList.toggle('active', !isDark);
  if (btnModeDark) btnModeDark.classList.toggle('active', isDark);

  // Header pill: labels vs canvas
  const ratio = StyleEngine.getContrastRatio(tokens.canvas, tokens.text);
  if (contrastValue) {
    contrastValue.textContent = `${ratio.toFixed(1)}:1 (${ratio >= 7.0 ? 'AAA' : (ratio >= 4.5 ? 'AA' : 'Fail')})`;
  }
  if (contrastPill) {
    contrastPill.className = 'contrast-pill';
    contrastPill.classList.add(ratio >= 7.0 ? 'pass-aaa' : (ratio >= 4.5 ? 'pass-aa' : 'fail'));
  }

  // Active preset highlight
  document.querySelectorAll('.preset-pill').forEach(pill => {
    const p = StyleEngine.PRESET_PALETTES[pill.dataset.preset];
    if (p) {
      const match = TOKEN_ORDER.every(k => tokens[k] && p[k] && tokens[k].toLowerCase() === p[k].toLowerCase());
      pill.classList.toggle('active', match);
    }
  });

  updateHoldUi();
  updateHarmonyBadge();
  updateReelsUi();
  updateColorWheelSvg();
  if (reelPopover && reelPopover.style.display !== 'none' && activePopoverToken) {
    updatePopoverContrast();
    updatePopoverActiveSwatch();
  }
}

// Toggle HOLD for a token
function toggleHold(tokenKey) {
  if (heldTokens[tokenKey] === undefined) return;
  heldTokens[tokenKey] = !heldTokens[tokenKey];
  updateHoldUi();
  updateReelsUi();
  updateColorWheelSvg();
  playSound('tick');
}

// Synchronize HOLD button visuals
function updateHoldUi() {
  const count = Object.values(heldTokens).filter(Boolean).length;

  document.querySelectorAll('.btn-hold').forEach(btn => {
    const key = btn.dataset.token || selectedWheelToken;
    const isHeld = !!heldTokens[key];
    btn.classList.toggle('is-held', isHeld);
    const textSpan = btn.querySelector('.hold-text');
    if (textSpan) textSpan.textContent = isHeld ? 'HELD' : 'HOLD';
  });

  if (shuffleLabel) {
    shuffleLabel.textContent = count === 6 ? 'ALL HELD' : 'SPIN';
  }
  if (btnShuffle) btnShuffle.disabled = count === 6;

  if (btnClearHolds) {
    btnClearHolds.style.display = count > 0 ? 'flex' : 'none';
    const span = btnClearHolds.querySelector('span');
    if (span) span.textContent = `Release holds (${count})`;
  }
}

function clearAllHolds() {
  Object.keys(heldTokens).forEach(k => { heldTokens[k] = false; });
  updateUiState();
  showToast('All holds released');
}

function updateHarmonyBadge() {
  if (!harmonyBadge) return;
  const labels = {
    triadic: 'Triadic 120°',
    complementary: 'Contrast 180°',
    'split-complementary': 'Split 150°/210°',
    analogous: 'Analogous 30°',
    tetradic: 'Tetradic Dual',
    square: 'Square 90°',
    monochrome: 'Single Hue',
    custom: 'Keep hues',
    random: 'Surprise'
  };
  harmonyBadge.textContent = labels[activeHarmony] || activeHarmony;
}

// Spin: compute the landing palette, then let the reels animate onto it
function executeHarmoniousShuffle(harmonyChoice) {
  if (isSpinning) return;
  const heldCount = Object.values(heldTokens).filter(Boolean).length;
  if (heldCount === 6) {
    showToast('All 6 reels are held — release one to spin');
    return;
  }

  const isDark = (currentMode === 'dark');
  const chosenHarmony = harmonyChoice || activeHarmony;
  let next;

  if (isMonochromeLocked || chosenHarmony === 'monochrome') {
    // Seed from a held reel if there is one, otherwise the anchor token
    const seedKey = [anchorToken, 'roads', 'water', 'canvas', 'greenspace', 'buildings', 'text'].find(k => k && heldTokens[k]) || anchorToken;
    const seed = (seedKey && tokens[seedKey]) ? tokens[seedKey] : StyleEngine.rgbToHex(...Object.values(StyleEngine.hslToRgb(Math.random() * 360, 60, 45)));
    const mono = StyleEngine.generateMonochromeTokens(seed, isDark);
    next = {};
    TOKEN_ORDER.forEach(k => { next[k] = heldTokens[k] ? tokens[k] : mono[k]; });
  } else {
    next = StyleEngine.generateHarmoniousPalette({
      isDark,
      harmony: chosenHarmony,
      currentTokens: tokens,
      held: heldTokens,
      anchorToken: anchorToken
    });
  }
  TOKEN_ORDER.forEach(k => { next[k] = next[k].toLowerCase(); });

  playSound('clunk');
  animateSpin(next, () => {
    tokens = { ...next };
    syncTokenInputs();
    updateUiState();
    applyCompiledStyle();
    const score = StyleEngine.scorePalette(tokens);
    if (score.passed === score.total) {
      playSound('win');
    } else if (score.passed < score.total) {
      showToast(`${score.total - score.passed} line${score.total - score.passed > 1 ? 's' : ''} below contrast — nudge a reel or hit Fix`);
    }
  });
}

// Step through the Colour Harmony dropdown choices and automatically spin to the new harmony
function stepHarmony(delta) {
  if (isSpinning || !selectHarmony) return;
  const options = Array.from(selectHarmony.options);
  if (!options.length) return;

  let currIdx = selectHarmony.selectedIndex;
  if (currIdx === -1) {
    currIdx = options.findIndex(opt => opt.value === activeHarmony);
    if (currIdx === -1) currIdx = 0;
  }

  const nextIdx = (currIdx + delta + options.length) % options.length;
  selectHarmony.selectedIndex = nextIdx;
  activeHarmony = options[nextIdx].value;
  updateHarmonyBadge();

  pullLever();
}

// Rotate the active harmony across the 360° color wheel by deltaDeg (e.g. +15° or -15°)
function rotateHarmony(deltaDeg) {
  if (isSpinning || !deltaDeg) return;

  const unheldKeys = TOKEN_ORDER.filter(k => !heldTokens[k]);
  if (unheldKeys.length === 0) {
    showToast('All reels are held — release one to rotate harmony');
    return;
  }

  unheldKeys.forEach(k => {
    const rgb = StyleEngine.hexToRgb(tokens[k]);
    const hsl = StyleEngine.rgbToHsl(rgb.r, rgb.g, rgb.b);
    const rotatedH = (hsl.h + deltaDeg + 360) % 360;
    const newColor = StyleEngine.rgbToHex(
      StyleEngine.hslToRgb(rotatedH, hsl.s, hsl.l).r,
      StyleEngine.hslToRgb(rotatedH, hsl.s, hsl.l).g,
      StyleEngine.hslToRgb(rotatedH, hsl.s, hsl.l).b
    ).toLowerCase();
    tokens[k] = newColor;
  });

  syncTokenInputs();
  updateUiState();
  applyCompiledStyle();
  playSound('tick');

  const baseH = Math.round(StyleEngine.rgbToHsl(
    StyleEngine.hexToRgb(tokens[anchorToken]).r,
    StyleEngine.hexToRgb(tokens[anchorToken]).g,
    StyleEngine.hexToRgb(tokens[anchorToken]).b
  ).h);
  showToast(`Rotated harmony ${deltaDeg > 0 ? '+' : ''}${deltaDeg}° (Base: ${baseH}°)`, 900);
}

// Select a token to inspect and control in the wheel toolbar
function selectWheelToken(tokenKey) {
  selectedWheelToken = tokenKey;
  updateColorWheelSvg();
  updateReelsUi();
  updateHoldUi();
  if (reelPopover && reelPopover.style.display !== 'none' && activePopoverToken) {
    updatePopoverContrast();
    updatePopoverActiveSwatch();
  }
}

// =====================================================================
//  SLOT MACHINE REELS
//  Each token is a 12-faced 3D drum. The front face is the live colour;
//  faces above are lighter and faces below darker, each one notch of
//  CIE L* apart, so every click is the same *perceived* change.
// =====================================================================

const FACE_COUNT = 12;
const FACE_ANGLE = 360 / FACE_COUNT;              // 30°
const FACE_HEIGHT = 30;                           // px
const REEL_RADIUS = (FACE_HEIGHT / 2) / Math.tan(Math.PI / FACE_COUNT); // ≈ 56px
const LSTAR_STEP = 5;                             // one notch = 5 L*
const reelState = {};
let isSpinning = false;

const mod = (n, m) => ((n % m) + m) % m;

function buildReels() {
  if (!reelsEl) return;
  reelsEl.innerHTML = '';

  TOKEN_ORDER.forEach((key, idx) => {
    const meta = TOKEN_META[key];
    const cap = key.charAt(0).toUpperCase() + key.slice(1);
    const col = document.createElement('div');
    col.className = 'reel-col';
    col.dataset.token = key;
    col.innerHTML = `
      <button type="button" class="btn-reel-base ${key === anchorToken ? 'is-base' : ''}" data-token="${key}" title="${key === anchorToken ? `Current Base Colour (${meta.name})` : `Set ${meta.name} as Base Colour`}">
        <span class="base-icon">🎯</span><span class="base-text">BASE</span>
      </button>
      <div class="reel-label" title="${meta.name}: ${meta.desc}"><span class="reel-icon">${meta.icon}</span><span>${meta.short}</span></div>
      <button type="button" class="reel-nudge" data-dir="1" title="Nudge lighter (+${LSTAR_STEP} L*)" aria-label="${meta.name} lighter">▲</button>
      <div class="reel-window" tabindex="0" role="slider" aria-label="${meta.name} lightness" title="Drag or scroll to change lightness · click to select">
        <div class="reel-drum"></div>
        <div class="reel-payline" aria-hidden="true"></div>
      </div>
      <button type="button" class="reel-nudge" data-dir="-1" title="Nudge darker (−${LSTAR_STEP} L*)" aria-label="${meta.name} darker">▼</button>
      <div class="reel-lamp" title=""><span class="lamp-dot"></span><span class="lamp-value">--</span></div>
      <div class="reel-hex-wrap">
        <button type="button" class="reel-chip" style="background:${tokens[key]}" title="Pick distinct colour for ${meta.name}"></button>
        <input type="text" id="text${cap}" class="reel-hex" value="${tokens[key]}" maxlength="7" spellcheck="false" aria-label="${meta.name} hex">
      </div>
      <button type="button" class="btn-hold reel-hold" data-token="${key}" title="Hold (${idx + 1})">
        <span class="hold-indicator"></span><span class="hold-text">HOLD</span>
      </button>
    `;
    reelsEl.appendChild(col);

    const baseBtn = col.querySelector('.btn-reel-base');
    if (baseBtn) {
      baseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        setAnchorToken(key);
      });
    }

    const drum = col.querySelector('.reel-drum');
    const faces = [];
    for (let i = 0; i < FACE_COUNT; i++) {
      const face = document.createElement('div');
      face.className = 'reel-face';
      face.style.transform = `rotateX(${i * FACE_ANGLE}deg) translateZ(${REEL_RADIUS}px)`;
      drum.appendChild(face);
      faces.push(face);
    }

    reelState[key] = { col, drum, faces, k: 0, phi: 0, dragging: false, spinning: false };
    const chipEl = col.querySelector('.reel-chip');
    TOKEN_INPUTS[key] = {
      // swatch chip stands in for the old native <input type=color>
      picker: { el: chipEl, set value(v) { chipEl.style.background = v; }, get value() { return chipEl.style.background; } },
      text: col.querySelector('.reel-hex')
    };
    chipEl.addEventListener('click', (e) => {
      e.preventDefault();
      openReelPopover(key);
    });
    const hexInput = col.querySelector('.reel-hex');
    if (hexInput) {
      hexInput.addEventListener('click', () => openReelPopover(key));
    }

    setupReelInteractions(key);
    paintReel(key);
  });
}

// Colour each face relative to the current token colour
function paintReel(key, baseHex = tokens[key]) {
  const st = reelState[key];
  if (!st) return;
  const front = mod(st.k, FACE_COUNT);
  const baseL = StyleEngine.getLstar(baseHex);
  st.faces.forEach((face, i) => {
    let d = mod(i - front, FACE_COUNT);
    if (d > FACE_COUNT / 2) d -= FACE_COUNT;
    const targetL = baseL + d * LSTAR_STEP;
    const color = d === 0 ? baseHex : StyleEngine.stepLightness(baseHex, d, LSTAR_STEP);
    face.style.background = color;
    face.classList.toggle('is-front', d === 0);
    face.classList.toggle('at-limit', d !== 0 && (targetL < 2 || targetL > 99));
    face.dataset.offset = d;
    face.textContent = d === 0 ? '' : `${Math.round(Math.min(99, Math.max(2, targetL)))}`;
    face.style.color = StyleEngine.getRelativeLuminance(color) > 0.3 ? 'rgba(0,0,0,.55)' : 'rgba(255,255,255,.6)';
  });
}

function setDrum(key, phi, { duration = 0, easing = 'ease-out' } = {}) {
  const st = reelState[key];
  st.phi = phi;
  st.drum.style.transition = duration ? `transform ${duration}ms ${easing}` : 'none';
  st.drum.style.transform = `translateZ(-${REEL_RADIUS}px) rotateX(${phi}deg)`;
}

// Commit a reel step: move the drum by `steps` notches and update the token
function nudgeReel(key, steps) {
  if (isSpinning || !steps) return;
  const st = reelState[key];
  const newHex = StyleEngine.stepLightness(tokens[key], steps, LSTAR_STEP);
  st.k += steps;
  setDrum(key, -st.k * FACE_ANGLE, { duration: 220, easing: 'cubic-bezier(.2,.9,.3,1.2)' });
  setTokenValue(key, newHex);
  paintReel(key);
  playSound('tick');
  bumpLamp(key);
}

function setupReelInteractions(key) {
  const st = reelState[key];
  const win = st.col.querySelector('.reel-window');

  // Drag to rotate
  let startY = 0, startPhi = 0, lastK = 0, moved = false;
  win.addEventListener('pointerdown', (e) => {
    if (isSpinning) return;
    win.setPointerCapture(e.pointerId);
    st.dragging = true;
    moved = false;
    startY = e.clientY;
    startPhi = st.phi;
    lastK = st.k;
    st.col.classList.add('is-dragging');
  });
  win.addEventListener('pointermove', (e) => {
    if (!st.dragging) return;
    const dy = e.clientY - startY;
    if (Math.abs(dy) > 3) moved = true;
    // dragging down brings the upper (lighter) faces down to the payline
    const phi = startPhi - dy * (FACE_ANGLE / FACE_HEIGHT);
    setDrum(key, phi);
    const k = Math.round(-phi / FACE_ANGLE);
    if (k !== lastK) {
      const newHex = StyleEngine.stepLightness(tokens[key], k - lastK, LSTAR_STEP);
      st.k = k;
      lastK = k;
      setTokenValue(key, newHex);
      paintReel(key);
      playSound('tick');
    }
  });
  const endDrag = () => {
    if (!st.dragging) return;
    st.dragging = false;
    st.col.classList.remove('is-dragging');
    setDrum(key, -st.k * FACE_ANGLE, { duration: 180, easing: 'cubic-bezier(.2,.9,.3,1.25)' });
    if (!moved) selectWheelToken(key);
    else bumpLamp(key);
  };
  win.addEventListener('pointerup', endDrag);
  win.addEventListener('pointercancel', endDrag);

  // Scroll wheel / trackpad
  let wheelAcc = 0;
  win.addEventListener('wheel', (e) => {
    e.preventDefault();
    wheelAcc += e.deltaY;
    if (Math.abs(wheelAcc) >= 40) {
      nudgeReel(key, wheelAcc > 0 ? -1 : 1);
      wheelAcc = 0;
    }
  }, { passive: false });

  // Keyboard on the reel itself
  win.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowUp') { e.preventDefault(); nudgeReel(key, 1); }
    if (e.key === 'ArrowDown') { e.preventDefault(); nudgeReel(key, -1); }
    if (e.key === 'Enter') selectWheelToken(key);
  });

  // Swatch drag-and-drop removed in favor of direct 1-click distinct color picker popover

  st.col.querySelectorAll('.reel-nudge').forEach(btn => {
    btn.addEventListener('click', () => nudgeReel(key, parseInt(btn.dataset.dir, 10)));
  });
}

// Set a token from any control, keep inputs in sync, recompile (debounced)
function setTokenValue(key, hex) {
  if (TOKEN_INPUTS[key]) {
    TOKEN_INPUTS[key].picker.value = hex;
    TOKEN_INPUTS[key].text.value = hex;
  }
  onTokenChanged(key, hex);
}

// Brief flash of a reel's lamp after it changes
function bumpLamp(key) {
  const lamp = reelState[key] && reelState[key].col.querySelector('.reel-lamp');
  if (!lamp) return;
  lamp.classList.remove('bump');
  void lamp.offsetWidth;
  lamp.classList.add('bump');
}

// Set a token as the base colour (harmony anchor)
function setAnchorToken(tokenKey) {
  if (!tokens[tokenKey]) return;
  anchorToken = tokenKey;
  updateReelsUi();
  updateColorWheelSvg();
  showToast(`Set ${TOKEN_META[anchorToken].name} as Base Colour 🎯`);
}

// Repaint all idle reels and the contrast lamps / marquee
function updateReelsUi() {
  TOKEN_ORDER.forEach(key => {
    const st = reelState[key];
    if (!st) return;
    if (!st.dragging && !st.spinning) paintReel(key);
    st.col.classList.toggle('is-held', !!heldTokens[key]);
    st.col.classList.toggle('is-selected', key === selectedWheelToken);
    st.col.classList.toggle('is-base-token', key === anchorToken);
    st.col.classList.toggle('is-popover-open', key === activePopoverToken);
    const baseBtn = st.col.querySelector('.btn-reel-base');
    if (baseBtn) {
      const isBase = (key === anchorToken);
      baseBtn.classList.toggle('is-base', isBase);
      baseBtn.title = isBase ? `Current Base Colour (${TOKEN_META[key].name})` : `Set ${TOKEN_META[key].name} as Base Colour`;
    }
  });
  const selBase = document.getElementById('selectBaseToken');
  if (selBase && selBase.value !== anchorToken) {
    selBase.value = anchorToken;
  }
  updateScoreUi();
}

function updateScoreUi() {
  const score = StyleEngine.scorePalette(tokens);
  TOKEN_ORDER.forEach(key => {
    const st = reelState[key];
    if (!st) return;
    const lamp = st.col.querySelector('.reel-lamp');
    const val = lamp.querySelector('.lamp-value');
    lamp.classList.remove('pass', 'fail', 'aaa', 'base');
    if (key === 'canvas') {
      lamp.classList.add('base');
      val.textContent = `L*${Math.round(StyleEngine.getLstar(tokens.canvas))}`;
      lamp.title = 'Canvas is the reference: every other reel is scored against it';
      return;
    }
    const line = score.lines[key];
    const rule = StyleEngine.CONTRAST_RULES[key];
    lamp.classList.add(line.pass ? 'pass' : 'fail');
    if (line.aaa) lamp.classList.add('aaa');
    val.textContent = line.ratio >= 10 ? line.ratio.toFixed(0) : line.ratio.toFixed(line.ratio >= 2 ? 1 : 2);
    lamp.title = `${rule.label}: ${line.ratio.toFixed(2)}:1 (needs ≥ ${rule.min}${rule.aaa ? `, AAA ≥ ${rule.aaa}` : ''})\n${rule.why}`;
  });

  if (marqueeStars) {
    marqueeStars.textContent = '★'.repeat(score.passed) + '☆'.repeat(score.total - score.passed);
  }
  if (marqueeText) {
    marqueeText.textContent = score.passed === score.total
      ? (score.lines.text.aaa ? 'ALL LINES (AAA)' : 'ALL LINES')
      : `${score.passed}/${score.total} LINES`;
  }
  if (slotCabinet) {
    slotCabinet.classList.toggle('is-all-pass', score.passed === score.total);
    slotCabinet.classList.toggle('is-jackpot', score.jackpot);
    slotCabinet.classList.toggle('has-fail', score.passed < score.total);
  }
  return score;
}

// ---- The Spin ----------------------------------------------------------

function pullLever() {
  if (!leverEl || isSpinning) return;
  leverEl.classList.remove('pulled');
  void leverEl.offsetWidth;
  leverEl.classList.add('pulled');
  setTimeout(() => leverEl.classList.remove('pulled'), 450);
  executeHarmoniousShuffle(activeHarmony);
}

function randomSymbolLike(hex) {
  // Same perceived lightness, random hue: plausible "symbols" flying past
  const rgb = StyleEngine.hexToRgb(hex);
  const hsl = StyleEngine.rgbToHsl(rgb.r, rgb.g, rgb.b);
  const h = Math.floor(Math.random() * 360);
  const c = StyleEngine.hslToRgb(h, Math.max(35, hsl.s), hsl.l);
  return StyleEngine.rgbToHex(c.r, c.g, c.b);
}

function animateSpin(finalTokens, onDone) {
  isSpinning = true;
  if (slotCabinet) slotCabinet.classList.add('is-spinning');
  const spinKeys = TOKEN_ORDER.filter(k => !heldTokens[k]);
  let remaining = spinKeys.length;
  if (!remaining) { isSpinning = false; onDone(); return; }

  spinKeys.forEach((key, j) => {
    const st = reelState[key];
    st.spinning = true;
    st.col.classList.add('is-spinning');

    const steps = FACE_COUNT * (2 + j) + Math.floor(Math.random() * FACE_COUNT);
    const targetK = st.k + steps;
    const landing = mod(targetK, FACE_COUNT);
    st.faces.forEach((face, i) => {
      face.textContent = '';
      face.classList.remove('is-front', 'at-limit');
      face.style.background = i === landing ? finalTokens[key] : randomSymbolLike(finalTokens[key]);
    });

    const duration = 900 + j * 260;
    setDrum(key, -targetK * FACE_ANGLE, { duration, easing: 'cubic-bezier(.12,.62,.22,1.04)' });

    // Tick sound while spinning, slowing down
    if (soundOn) {
      let t = 0;
      const tickLoop = () => {
        if (t > duration * 0.85) return;
        playSound('tick');
        const gap = 40 + (t / duration) * 160;
        t += gap;
        setTimeout(tickLoop, gap);
      };
      tickLoop();
    }

    setTimeout(() => st.col.classList.remove('is-spinning'), duration * 0.55);
    setTimeout(() => {
      st.k = targetK;
      st.spinning = false;
      tokens[key] = finalTokens[key];
      if (TOKEN_INPUTS[key]) {
        TOKEN_INPUTS[key].picker.value = finalTokens[key];
        TOKEN_INPUTS[key].text.value = finalTokens[key];
      }
      st.col.classList.add('landed');
      setTimeout(() => st.col.classList.remove('landed'), 300);
      playSound('clunk');
      paintReel(key);
      updateScoreUi();
      remaining--;
      if (remaining === 0) {
        isSpinning = false;
        if (slotCabinet) slotCabinet.classList.remove('is-spinning');
        onDone();
      }
    }, duration + 30);
  });
}

// ---- Sound (off by default) ---------------------------------------------

let soundOn = false;
let audioCtx = null;

function playSound(kind) {
  if (!soundOn) return;
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const now = audioCtx.currentTime;
    const blip = (freq, start, len, type = 'square', vol = 0.035) => {
      const o = audioCtx.createOscillator();
      const g = audioCtx.createGain();
      o.type = type;
      o.frequency.value = freq;
      g.gain.setValueAtTime(vol, now + start);
      g.gain.exponentialRampToValueAtTime(0.0001, now + start + len);
      o.connect(g).connect(audioCtx.destination);
      o.start(now + start);
      o.stop(now + start + len + 0.02);
    };
    if (kind === 'tick') blip(1400, 0, 0.018);
    if (kind === 'clunk') blip(160, 0, 0.09, 'triangle', 0.12);
    if (kind === 'win') [523, 659, 784, 1046].forEach((f, i) => blip(f, i * 0.09, 0.16, 'square', 0.05));
  } catch (err) { /* audio unavailable */ }
}

function setupLever() {
  if (!leverEl) return;
  let startY = null;
  let pulledEnough = false;
  leverEl.addEventListener('pointerdown', (e) => {
    if (isSpinning) return;
    leverEl.setPointerCapture(e.pointerId);
    startY = e.clientY;
    pulledEnough = false;
    leverEl.classList.add('grabbing');
  });
  leverEl.addEventListener('pointermove', (e) => {
    if (startY === null) return;
    const dy = Math.max(0, Math.min(70, e.clientY - startY));
    leverArm.style.transform = `translateY(${dy}px)`;
    pulledEnough = dy > 40;
  });
  const release = () => {
    if (startY === null) return;
    const wasDrag = pulledEnough;
    startY = null;
    leverEl.classList.remove('grabbing');
    leverArm.style.transform = '';
    // A drag past the threshold or a simple click both pull the lever
    if (wasDrag) executeHarmoniousShuffle(activeHarmony);
    else pullLever();
  };
  leverEl.addEventListener('pointerup', release);
  leverEl.addEventListener('pointercancel', () => { startY = null; leverArm.style.transform = ''; leverEl.classList.remove('grabbing'); });
  leverEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pullLever(); }
  });

  if (btnSound) {
    btnSound.addEventListener('click', () => {
      soundOn = !soundOn;
      btnSound.textContent = soundOn ? '🔊' : '🔇';
      btnSound.title = `Sound effects (${soundOn ? 'on' : 'off'})`;
      btnSound.setAttribute('aria-pressed', String(soundOn));
      if (soundOn) playSound('tick');
    });
  }
}


// =====================================================================
//  DISTINCT COLOURS POPOVER
//  Replaces continuous wheel dragging and messy swatch bars with curated,
//  distinct cartographic swatches organized into 3 clear categories.
// =====================================================================

const DISTINCT_PALETTES = {
  accents: [
    { name: 'Crimson', hex: '#e11d48' },
    { name: 'Rose', hex: '#f43f5e' },
    { name: 'Rust', hex: '#c2410c' },
    { name: 'Flame', hex: '#ea580c' },
    { name: 'Amber', hex: '#d97706' },
    { name: 'Sunflower', hex: '#eab308' },
    { name: 'Lime', hex: '#65a30d' },
    { name: 'Emerald', hex: '#059669' },
    { name: 'Mint', hex: '#10b981' },
    { name: 'Teal', hex: '#0d9488' },
    { name: 'Cyan', hex: '#0284c7' },
    { name: 'Sky', hex: '#38bdf8' },
    { name: 'Royal Blue', hex: '#2563eb' },
    { name: 'Indigo', hex: '#4f46e5' },
    { name: 'Violet', hex: '#7c3aed' },
    { name: 'Magenta', hex: '#c026d3' }
  ],
  softs: [
    { name: 'Soft Blue', hex: '#bfdbfe' },
    { name: 'Pale Ice', hex: '#e0f2fe' },
    { name: 'Glacier', hex: '#cffafe' },
    { name: 'Deep Sea', hex: '#1e3a5f' },
    { name: 'Navy Basin', hex: '#1e293b' },
    { name: 'Spring Park', hex: '#bbf7d0' },
    { name: 'Mint Wash', hex: '#dcfce7' },
    { name: 'Forest Green', hex: '#15803d' },
    { name: 'Dark Pine', hex: '#14532d' },
    { name: 'Olive Sage', hex: '#d9f99d' },
    { name: 'Warm Parchment', hex: '#fef9c3' },
    { name: 'Sandstone', hex: '#fef3c7' },
    { name: 'Desert Buff', hex: '#fed7aa' },
    { name: 'Terracotta', hex: '#fb923c' },
    { name: 'Warm Blush', hex: '#ffe4e6' },
    { name: 'Lavender Wash', hex: '#ede9fe' }
  ],
  neutrals: [
    { name: 'Pure White', hex: '#ffffff' },
    { name: 'Warm White', hex: '#fafaf9' },
    { name: 'Porcelain', hex: '#f8fafc' },
    { name: 'Platinum', hex: '#f1f5f9' },
    { name: 'Light Slate', hex: '#e2e8f0' },
    { name: 'Ash Grey', hex: '#cbd5e1' },
    { name: 'Medium Grey', hex: '#94a3b8' },
    { name: 'Muted Slate', hex: '#64748b' },
    { name: 'Steel', hex: '#475569' },
    { name: 'Dark Charcoal', hex: '#334155' },
    { name: 'Dark Navy', hex: '#1e293b' },
    { name: 'Deep Slate', hex: '#0f172a' },
    { name: 'Pitch Black', hex: '#020617' },
    { name: 'Jet Black', hex: '#000000' },
    { name: 'Warm Stone', hex: '#d6d3d1' },
    { name: 'Dark Bronze', hex: '#292524' }
  ]
};

// Popover DOM References
const reelPopover = document.getElementById('reelPopover');
const popoverTokenIcon = document.getElementById('popoverTokenIcon');
const popoverTokenName = document.getElementById('popoverTokenName');
const popoverCurrentChip = document.getElementById('popoverCurrentChip');
const btnPopoverClose = document.getElementById('btnPopoverClose');
const popoverAccentGrid = document.getElementById('popoverAccentGrid');
const popoverSoftGrid = document.getElementById('popoverSoftGrid');
const popoverNeutralGrid = document.getElementById('popoverNeutralGrid');
const popoverHexInput = document.getElementById('popoverHexInput');
const popoverContrastBadge = document.getElementById('popoverContrastBadge');

let activePopoverToken = null;

function makePopoverSwatchButton(item) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'btn-popover-swatch';
  btn.style.background = item.hex;
  btn.dataset.hex = item.hex;
  btn.title = `${item.name} (${item.hex.toUpperCase()})`;
  btn.setAttribute('aria-label', `${item.name} ${item.hex}`);
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    selectPopoverSwatch(item.hex);
  });
  return btn;
}

function buildPopoverSwatches() {
  if (popoverAccentGrid) {
    popoverAccentGrid.innerHTML = '';
    DISTINCT_PALETTES.accents.forEach(item => popoverAccentGrid.appendChild(makePopoverSwatchButton(item)));
  }
  if (popoverSoftGrid) {
    popoverSoftGrid.innerHTML = '';
    DISTINCT_PALETTES.softs.forEach(item => popoverSoftGrid.appendChild(makePopoverSwatchButton(item)));
  }
  if (popoverNeutralGrid) {
    popoverNeutralGrid.innerHTML = '';
    DISTINCT_PALETTES.neutrals.forEach(item => popoverNeutralGrid.appendChild(makePopoverSwatchButton(item)));
  }
}

function openReelPopover(tokenKey) {
  if (!tokenKey || !tokens[tokenKey] || isSpinning) return;
  activePopoverToken = tokenKey;
  selectedWheelToken = tokenKey;

  const meta = TOKEN_META[tokenKey];
  if (popoverTokenIcon) popoverTokenIcon.textContent = meta.icon;
  if (popoverTokenName) popoverTokenName.textContent = `${meta.name} (${meta.desc})`;
  if (popoverCurrentChip) popoverCurrentChip.style.background = tokens[tokenKey];
  if (popoverHexInput) popoverHexInput.value = tokens[tokenKey];

  updatePopoverContrast();
  updatePopoverActiveSwatch();
  updateReelsUi();

  if (reelPopover) {
    reelPopover.style.display = 'flex';
  }
}

function closeReelPopover() {
  if (!reelPopover || reelPopover.style.display === 'none') return;
  reelPopover.style.display = 'none';
  activePopoverToken = null;
  updateReelsUi();
}

function selectPopoverSwatch(hex) {
  if (!activePopoverToken || isSpinning || !hex) return;
  const normHex = hex.toLowerCase();
  tokens[activePopoverToken] = normHex;

  if (TOKEN_INPUTS[activePopoverToken]) {
    TOKEN_INPUTS[activePopoverToken].picker.value = normHex;
    TOKEN_INPUTS[activePopoverToken].text.value = normHex;
  }

  paintReel(activePopoverToken);
  if (popoverCurrentChip) popoverCurrentChip.style.background = normHex;
  if (popoverHexInput) popoverHexInput.value = normHex;

  bumpLamp(activePopoverToken);
  playSound('tick');
  updateUiState();

  clearTimeout(compileTimeout);
  compileTimeout = setTimeout(() => {
    applyCompiledStyle();
  }, 80);
}

function updatePopoverContrast() {
  if (!activePopoverToken || !popoverContrastBadge) return;
  const currentHex = tokens[activePopoverToken];
  if (activePopoverToken === 'canvas') {
    const score = StyleEngine.scorePalette(tokens);
    popoverContrastBadge.textContent = `${score.passed}/${score.total} Lines (${score.passed === score.total ? 'All Pass' : 'Review'})`;
    popoverContrastBadge.className = 'popover-contrast-badge ' + (score.passed === score.total ? 'pass' : 'fail');
  } else {
    const ratio = StyleEngine.getContrastRatio(tokens.canvas, currentHex);
    const rule = StyleEngine.CONTRAST_RULES[activePopoverToken];
    const isAaa = ratio >= (rule.aaa || 7.0);
    const isPass = ratio >= (rule.min || 3.0);
    popoverContrastBadge.textContent = `${ratio.toFixed(1)}:1 (${isAaa ? 'AAA' : (isPass ? 'Pass' : 'Fail')})`;
    popoverContrastBadge.className = 'popover-contrast-badge ' + (isAaa ? 'aaa' : (isPass ? 'pass' : 'fail'));
  }
}

function updatePopoverActiveSwatch() {
  if (!activePopoverToken || !reelPopover) return;
  const currentHex = (tokens[activePopoverToken] || '').toLowerCase();
  reelPopover.querySelectorAll('.btn-popover-swatch').forEach(btn => {
    const isMatch = (btn.dataset.hex || '').toLowerCase() === currentHex;
    btn.classList.toggle('is-active', isMatch);
  });
}

function paintToken(key, hex) {
  if (isSpinning || !key) return;
  if (tokens[key] && tokens[key].toLowerCase() === hex.toLowerCase()) return;
  setTokenValue(key, hex.toLowerCase());
  bumpLamp(key);
  playSound('tick');
}

// --- Adobe-Style Color Wheel ---

// Render high-DPI chromatic saturation disc onto HTML5 canvas
function renderColorWheelCanvas() {
  if (!colorWheelCanvas) return;
  const ctx = colorWheelCanvas.getContext('2d');
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const cssSize = 260;
  const width = Math.round(cssSize * dpr);
  const height = Math.round(cssSize * dpr);

  colorWheelCanvas.width = width;
  colorWheelCanvas.height = height;
  colorWheelCanvas.style.width = `${cssSize}px`;
  colorWheelCanvas.style.height = `${cssSize}px`;

  const centerX = width / 2;
  const centerY = height / 2;
  const radius = width / 2; // fill the full 260px diameter circle

  const imgData = ctx.createImageData(width, height);
  const data = imgData.data;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const dx = x - centerX;
      const dy = y - centerY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist <= radius) {
        let angle = Math.atan2(dy, dx) * (180 / Math.PI);
        if (angle < 0) angle += 360;

        const sat = Math.min(100, (dist / radius) * 100);
        // Render at L=50 for pure vivid chroma wheel
        const rgb = StyleEngine.hslToRgb(angle, sat, 50);

        const idx = (y * width + x) * 4;
        data[idx] = rgb.r;
        data[idx + 1] = rgb.g;
        data[idx + 2] = rgb.b;

        // Smooth antialiased edge
        const edge = radius - dist;
        const alpha = edge < (1.2 * dpr) ? Math.max(0, Math.min(255, Math.round((edge / (1.2 * dpr)) * 255))) : 255;
        data[idx + 3] = alpha;
      }
    }
  }
  ctx.putImageData(imgData, 0, 0);
}

// Convert Token to Color Wheel Polar Position
function getTokenWheelPos(tokenKey) {
  const hex = tokens[tokenKey] || '#ffffff';
  const rgb = StyleEngine.hexToRgb(hex);
  const hsl = StyleEngine.rgbToHsl(rgb.r, rgb.g, rgb.b);

  const centerX = 130;
  const centerY = 130;
  const maxRadius = 118;

  const angleRad = (hsl.h * Math.PI) / 180;
  // Radius mapped from saturation [0, 100] -> [14, maxRadius]
  const r = 14 + (hsl.s / 100) * (maxRadius - 14);

  const x = centerX + r * Math.cos(angleRad);
  const y = centerY + r * Math.sin(angleRad);

  return { x, y, r, h: hsl.h, s: hsl.s, l: hsl.l, hex };
}

// Render SVG Spokes, Polygon, and Draggable Pins
function updateColorWheelSvg() {
  if (!colorWheelSvg) return;
  colorWheelSvg.innerHTML = '';

  const centerX = 130;
  const centerY = 130;

  // Calculate coordinates for all 6 tokens
  const keys = ['canvas', 'water', 'greenspace', 'roads', 'buildings', 'text'];
  const positions = {};
  keys.forEach(k => {
    positions[k] = getTokenWheelPos(k);
  });

  // 1. Draw spokes from center to each pin
  keys.forEach(k => {
    const pos = positions[k];
    const spoke = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    spoke.setAttribute('x1', centerX);
    spoke.setAttribute('y1', centerY);
    spoke.setAttribute('x2', pos.x);
    spoke.setAttribute('y2', pos.y);
    spoke.setAttribute('class', 'wheel-spoke');
    colorWheelSvg.appendChild(spoke);
  });

  // 2. Draw harmony connecting polygon (in order of angle)
  const sortedKeys = [...keys].sort((a, b) => positions[a].h - positions[b].h);
  const pointsStr = sortedKeys.map(k => `${positions[k].x},${positions[k].y}`).join(' ');
  const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
  poly.setAttribute('points', pointsStr);
  poly.setAttribute('class', 'wheel-polygon');
  colorWheelSvg.appendChild(poly);

  // 3. Center pivot dot
  const centerDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  centerDot.setAttribute('cx', centerX);
  centerDot.setAttribute('cy', centerY);
  centerDot.setAttribute('r', '4');
  centerDot.setAttribute('fill', '#ffffff');
  centerDot.setAttribute('opacity', '0.6');
  colorWheelSvg.appendChild(centerDot);

  // 4. Draw interactive pin groups
  keys.forEach(k => {
    const pos = positions[k];
    const isAnchor = (k === anchorToken);
    const isHeld = !!heldTokens[k];
    const isSelected = (k === selectedWheelToken);
    const meta = TOKEN_META[k];

    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', `wheel-pin-group ${k === draggingWheelPin ? 'is-dragging' : ''}`);
    group.setAttribute('data-token', k);
    group.setAttribute('transform', `translate(${pos.x}, ${pos.y})`);

    // Pulsing target ring for Anchor token
    if (isAnchor) {
      const anchorRing = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      anchorRing.setAttribute('r', '17');
      anchorRing.setAttribute('class', 'wheel-pin-anchor-ring');
      group.appendChild(anchorRing);
    }

    // Outer halo
    const halo = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    halo.setAttribute('r', isSelected ? '14' : '12');
    halo.setAttribute('class', 'wheel-pin-halo');
    halo.setAttribute('stroke', isAnchor ? '#38bdf8' : (isHeld ? '#f59e0b' : '#ffffff'));
    halo.setAttribute('stroke-width', isSelected ? '3.5' : '2.5');
    group.appendChild(halo);

    // Inner color fill
    const fillCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    fillCircle.setAttribute('r', isSelected ? '12' : '10');
    fillCircle.setAttribute('fill', pos.hex);
    group.appendChild(fillCircle);

    // Emoji icon
    const iconText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    iconText.setAttribute('font-size', isSelected ? '11' : '9');
    iconText.setAttribute('text-anchor', 'middle');
    iconText.setAttribute('dominant-baseline', 'central');
    iconText.textContent = meta.icon;
    group.appendChild(iconText);

    // Lock badge if held
    if (isHeld) {
      const lockBadge = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      lockBadge.setAttribute('x', '7');
      lockBadge.setAttribute('y', '-7');
      lockBadge.setAttribute('font-size', '10');
      lockBadge.textContent = '🔒';
      group.appendChild(lockBadge);
    }

    // Event listener for selecting token and opening distinct colour picker popover
    group.addEventListener('pointerdown', (e) => {
      e.stopPropagation();
      e.preventDefault();
      selectWheelToken(k);
      openReelPopover(k);
    });

    colorWheelSvg.appendChild(group);
  });
}

// Setup interactions for the color wheel
function setupColorWheelInteractions() {
  // Pin dragging removed: clicking any pin selects it and opens the distinct color popover.
  // Harmony rotation is handled cleanly via the ◀ / ▶ buttons.
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
      if (isSpinning) return;
      TOKEN_ORDER.forEach(k => { tokens[k] = p[k]; });
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
  btnModeLight.addEventListener('click', () => {
    if (currentMode === 'light' || isSpinning) return;
    setThemeMode('light');
  });
  btnModeDark.addEventListener('click', () => {
    if (currentMode === 'dark' || isSpinning) return;
    setThemeMode('dark');
  });

  locationSelect.addEventListener('change', (e) => {
    const p = PRESETS[e.target.value];
    if (p && map) {
      map.flyTo({ center: p.center, zoom: p.zoom, pitch: p.pitch, bearing: p.bearing, essential: true, duration: 1800 });
    }
  });

  btnProjMercator.addEventListener('click', () => {
    currentProjection = 'mercator';
    btnProjMercator.classList.add('active');
    btnProjGlobe.classList.remove('active');
    if (map) map.setProjection({ type: 'mercator' });
  });
  btnProjGlobe.addEventListener('click', () => {
    currentProjection = 'globe';
    btnProjGlobe.classList.add('active');
    btnProjMercator.classList.remove('active');
    if (map) map.setProjection({ type: 'globe' });
  });

  // Reel HOLD buttons
  document.querySelectorAll('.reel-hold').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleHold(btn.dataset.token);
    });
  });

  // Base colour selector
  const selectBaseToken = document.getElementById('selectBaseToken');
  if (selectBaseToken) {
    selectBaseToken.value = anchorToken;
    selectBaseToken.addEventListener('change', (e) => {
      setAnchorToken(e.target.value);
    });
  }

  // Harmony ("game") selector: changing selection triggers spin
  if (selectHarmony) {
    selectHarmony.addEventListener('change', (e) => {
      activeHarmony = e.target.value;
      updateHarmonyBadge();
      pullLever();
    });
  }

  // Left/Right buttons next to Colour harmony cycle choices and auto-spin
  if (btnPrevHarmony) btnPrevHarmony.addEventListener('click', () => stepHarmony(-1));
  if (btnNextHarmony) btnNextHarmony.addEventListener('click', () => stepHarmony(1));

  if (btnWheelRotateCcw) btnWheelRotateCcw.addEventListener('click', () => rotateHarmony(-15));
  if (btnWheelRotateCw) btnWheelRotateCw.addEventListener('click', () => rotateHarmony(15));
  if (btnClearHolds) btnClearHolds.addEventListener('click', clearAllHolds);
  btnShuffle.addEventListener('click', pullLever);

  if (btnPopoverClose) {
    btnPopoverClose.addEventListener('click', closeReelPopover);
  }
  if (popoverHexInput) {
    popoverHexInput.addEventListener('input', (e) => {
      let val = e.target.value.trim();
      if (!val.startsWith('#')) val = '#' + val;
      if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
        selectPopoverSwatch(val);
      }
    });
  }

  // Close popover when clicking outside
  document.addEventListener('pointerdown', (e) => {
    if (!reelPopover || reelPopover.style.display === 'none') return;
    if (reelPopover.contains(e.target)) return;
    if (e.target.closest && (e.target.closest('.reel-chip') || e.target.closest('.reel-hex') || e.target.closest('.wheel-pin-group'))) return;
    closeReelPopover();
  });

  btnAutoContrast.addEventListener('click', () => {
    if (isSpinning) return;
    const before = { ...tokens };
    tokens = StyleEngine.autoBalanceContrast(tokens);
    const changed = TOKEN_ORDER.filter(k => before[k].toLowerCase() !== tokens[k].toLowerCase());
    syncTokenInputs();
    updateUiState();
    applyCompiledStyle();
    changed.forEach(bumpLamp);
    showToast(changed.length
      ? `Fixed ${changed.map(k => TOKEN_META[k].short.toLowerCase()).join(', ')} with the smallest lightness change`
      : 'Every line already passes ✓');
  });

  btnMonoLock.addEventListener('click', () => {
    isMonochromeLocked = !isMonochromeLocked;
    btnMonoLock.classList.toggle('active', isMonochromeLocked);
    if (isMonochromeLocked) {
      const isDark = (currentMode === 'dark');
      tokens = StyleEngine.generateMonochromeTokens(tokens.roads || tokens.canvas, isDark);
      syncTokenInputs();
      updateUiState();
      applyCompiledStyle();
      showToast('Monochrome lock on — roads & canvas drive every reel');
    } else {
      showToast('Monochrome lock off');
    }
  });

  btnShare.addEventListener('click', () => {
    saveTokensToUrl();
    navigator.clipboard.writeText(window.location.href).then(() => {
      showToast('Shareable URL copied to clipboard!');
    }).catch(() => {
      showToast('URL updated in address bar');
    });
  });

  btnInspect.addEventListener('click', () => {
    inspectorDrawer.classList.toggle('open');
    updateInspectorJson();
  });
  btnCloseInspector.addEventListener('click', () => inspectorDrawer.classList.remove('open'));

  btnCopyJson.addEventListener('click', () => {
    if (!currentStyle) return;
    navigator.clipboard.writeText(JSON.stringify(currentStyle, null, 2)).then(() => {
      showToast('Style JSON copied to clipboard!');
    });
  });

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

  // Keyboard: Space = spin, 1–6 = hold reel
  document.addEventListener('keydown', (e) => {
    const t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.code === 'Space' && !(t && t.classList && t.classList.contains('reel-window'))) {
      if (t && t.tagName === 'BUTTON') return; // let buttons handle their own Space
      e.preventDefault();
      pullLever();
    }
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= 6) toggleHold(TOKEN_ORDER[n - 1]);

    // Keyboard rotation: [ or Shift+Left = counter-clockwise, ] or Shift+Right = clockwise
    if (e.key === '[' || (e.shiftKey && e.key === 'ArrowLeft')) {
      e.preventDefault();
      rotateHarmony(-15);
    }
    if (e.key === ']' || (e.shiftKey && e.key === 'ArrowRight')) {
      e.preventDefault();
      rotateHarmony(15);
    }

    // Keyboard: Escape closes popover
    if (e.key === 'Escape') {
      closeReelPopover();
    }
  });

  window.addEventListener('resize', () => {
    renderColorWheelCanvas();
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
