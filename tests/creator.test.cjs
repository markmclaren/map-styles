const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { JSDOM } = require('jsdom');

const ROOT = path.resolve(__dirname, '..');
const DOCS = path.join(ROOT, 'docs');
const TOKENS = ['canvas', 'water', 'greenspace', 'roads', 'buildings', 'text'];
const DEFAULT_TOKENS = {
  canvas: '#f8fafc',
  water: '#cbd5e1',
  greenspace: '#e2e8f0',
  roads: '#475569',
  buildings: '#e2e8f0',
  text: '#0f172a'
};
const TOKEN_INPUT_IDS = {
  canvas: 'Canvas',
  water: 'Water',
  greenspace: 'Greenspace',
  roads: 'Roads',
  buildings: 'Buildings',
  text: 'Text'
};

const html = fs.readFileSync(path.join(DOCS, 'creator.html'), 'utf8');
const styleEngineSource = fs.readFileSync(path.join(DOCS, 'style-engine.js'), 'utf8');
const baseTemplateSource = fs.readFileSync(path.join(DOCS, 'dist', 'bright-template.js'), 'utf8');
const creatorSource = fs.readFileSync(path.join(DOCS, 'creator.js'), 'utf8');

function suppressCreatorStartup(source) {
  const startup = /\n\/\/ Launch safely regardless of document ready state\nif \(document\.readyState === 'loading'\) \{\n  document\.addEventListener\('DOMContentLoaded', init\);\n\} else \{\n  init\(\);\n\}\s*$/;
  assert.match(source, startup, 'creator.js startup block must remain removable for deterministic controller tests');
  return source.replace(startup, '\n');
}

const TEST_HOOKS = `
window.__creatorTestHooks = Object.freeze({
  init,
  onTokenChanged,
  syncTokenInputs,
  updateUiState,
  setStudioView,
  executeHarmoniousShuffle,
  setThemeMode,
  loadTokensFromUrl,
  applyCompiledStyle,
  selectWheelToken,
  toggleHold,
  clearAllHolds,
  renderPresetPills,
  get tokens() { return { ...tokens }; },
  setTokens(nextTokens) { tokens = { ...nextTokens }; },
  get heldTokens() { return { ...heldTokens }; },
  setHeld(nextHeld) { heldTokens = { ...heldTokens, ...nextHeld }; },
  setMonochromeLocked(value) { isMonochromeLocked = Boolean(value); },
  get currentStyle() { return currentStyle; },
  get map() { return map; }
});
`;

function installCanvasStub(window) {
  window.HTMLCanvasElement.prototype.getContext = function getContext() {
    return {
      scale() {},
      createImageData(width, height) {
        return { data: new Uint8ClampedArray(width * height * 4) };
      },
      putImageData() {}
    };
  };
}

function installMapLibreStub(window) {
  const maps = [];

  class FakeMap {
    constructor(options) {
      this.options = options;
      this.calls = [];
      this.style = options.style;
      this.center = { lng: options.center[0], lat: options.center[1] };
      this.zoom = options.zoom;
      maps.push(this);
    }

    addControl(control, position) {
      this.calls.push(['addControl', control, position]);
      return this;
    }

    on(event, handler) {
      this.calls.push(['on', event]);
      this.handlers ??= {};
      this.handlers[event] = handler;
      return this;
    }

    once(event, handler) {
      this.calls.push(['once', event]);
      if (handler) handler();
      return this;
    }

    setStyle(style) {
      this.calls.push(['setStyle', style]);
      this.style = style;
      return this;
    }

    setProjection(projection) {
      this.calls.push(['setProjection', projection]);
      this.projection = projection;
      return this;
    }

    flyTo(options) {
      this.calls.push(['flyTo', options]);
      return this;
    }

    getCenter() {
      return this.center;
    }

    getZoom() {
      return this.zoom;
    }

    getStyle() {
      return this.style;
    }
  }

  window.maplibregl = {
    Map: FakeMap,
    NavigationControl: class NavigationControl {
      constructor(options) { this.options = options; }
    },
    GlobeControl: class GlobeControl {}
  };
  return maps;
}

function createCreator(url = 'https://example.test/creator.html') {
  const dom = new JSDOM(html, {
    url,
    runScripts: 'outside-only',
    pretendToBeVisual: true
  });
  const { window } = dom;
  const errors = [];
  const downloaded = [];

  installCanvasStub(window);
  const maps = installMapLibreStub(window);
  window.console.warn = () => {};
  window.console.error = (...args) => errors.push(args);
  window.navigator.clipboard = { writeText: async () => {} };
  window.URL.createObjectURL = () => 'blob:creator-test';
  window.URL.revokeObjectURL = () => {};
  window.HTMLAnchorElement.prototype.click = function click() {
    downloaded.push({ download: this.download, href: this.href });
  };

  window.eval(styleEngineSource);
  window.eval(baseTemplateSource);
  window.eval(`${suppressCreatorStartup(creatorSource)}\n${TEST_HOOKS}`);

  return {
    dom,
    window,
    document: window.document,
    hooks: window.__creatorTestHooks,
    maps,
    errors,
    downloaded,
    close() { dom.window.close(); }
  };
}

async function initializedCreator(url) {
  const creator = createCreator(url);
  await creator.hooks.init();
  return creator;
}

function inputFor(document, token) {
  const suffix = TOKEN_INPUT_IDS[token];
  const input = document.getElementById(`text${suffix}`);
  assert.ok(input, `#text${suffix} precise hex input should be retained for ${token}`);
  return input;
}

function editorFor(document, token) {
  const trigger = document.querySelector(`.token-trigger[data-token="${token}"]`);
  assert.ok(trigger, `${token} needs a .token-trigger[data-token] row`);
  const row = trigger.closest('[data-token]') || trigger.parentElement;
  const editorId = trigger.getAttribute('aria-controls');
  const editor = (editorId && document.getElementById(editorId)) || row?.querySelector('.token-editor') || document.querySelector(`.token-editor[data-token="${token}"]`);
  assert.ok(editor, `${token} trigger needs a matching .token-editor`);
  return { trigger, editor };
}

function normalizeHex(value) {
  const match = String(value || '').trim().match(/^#?([0-9a-f]{6})$/i);
  return match ? `#${match[1].toLowerCase()}` : null;
}

function suggestionHex(swatch) {
  const explicit = swatch.dataset.color || swatch.dataset.colour || swatch.dataset.hex || swatch.dataset.value;
  const direct = normalizeHex(explicit);
  if (direct) return direct;

  const styleValue = swatch.style.backgroundColor;
  const hex = normalizeHex(styleValue);
  if (hex) return hex;
  const rgb = styleValue.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/i);
  if (rgb) {
    return `#${rgb.slice(1).map(channel => Number(channel).toString(16).padStart(2, '0')).join('')}`;
  }
  return null;
}

function dispatchInput(window, input, value) {
  input.value = value;
  input.dispatchEvent(new window.Event('input', { bubbles: true }));
}

test('the simplified creator defaults to six closed card editors with Advanced tools collapsed', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());

  const { document } = creator;
  const triggers = [...document.querySelectorAll('.token-trigger')];
  assert.equal(triggers.length, TOKENS.length, 'exactly six semantic card rows are rendered');
  assert.deepEqual(triggers.map(trigger => trigger.dataset.token), TOKENS, 'card rows preserve the six semantic token order');

  for (const token of TOKENS) {
    const { trigger, editor } = editorFor(document, token);
    assert.equal(trigger.getAttribute('aria-expanded'), 'false', `${token} starts closed`);
    assert.equal(editor.hidden, true, `${token} editor starts hidden`);
  }

  const advancedTools = document.querySelector('details#advancedTools');
  assert.ok(advancedTools, 'nonessential controls live in #advancedTools');
  assert.equal(advancedTools.open, false, 'Advanced tools are collapsed by default');
  assert.ok(document.getElementById('tokenGrid'), 'cards remain the default visible editing surface');
});

test('one card editor opens at a time and swatches synchronize all six token inputs', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());

  const { document, window, hooks } = creator;
  for (const token of TOKENS) {
    const { trigger, editor } = editorFor(document, token);
    trigger.click();
    assert.equal(editor.hidden, false, `${token} editor opens from its card row`);

    for (const otherToken of TOKENS.filter(key => key !== token)) {
      assert.equal(editorFor(document, otherToken).editor.hidden, true, `opening ${token} closes ${otherToken}`);
    }

    const suggestions = [...editor.querySelectorAll('.suggested-swatch')];
    assert.ok(suggestions.length > 0, `${token} exposes suggested-swatch choices`);
    const before = hooks.tokens[token];
    const swatch = suggestions.find(item => suggestionHex(item) && suggestionHex(item) !== before) || suggestions[0];
    const expected = suggestionHex(swatch);
    assert.ok(expected, 'each suggested swatch exposes a concrete six-digit color through data-color/data-hex/data-value or inline color');

    swatch.click();
    assert.equal(hooks.tokens[token], expected, `${token} state follows its suggested swatch`);
    assert.equal(inputFor(document, token).value.toLowerCase(), expected, `${token} exact input stays synchronized`);
    assert.equal(document.getElementById(`picker${TOKEN_INPUT_IDS[token]}`).value.toLowerCase(), expected, `${token} native picker stays synchronized`);
  }

  // Opening an already-open row closes it without changing its semantic color.
  const roads = editorFor(document, 'roads');
  roads.trigger.click();
  roads.trigger.click();
  assert.equal(roads.editor.hidden, true, 'the open card toggles closed');
  assert.match(hooks.tokens.roads, /^#[0-9a-f]{6}$/i, 'closing a card preserves its token');

  // Keep the test explicit about real DOM events instead of direct controller calls.
  dispatchInput(window, inputFor(document, 'roads'), '#123abc');
  assert.equal(hooks.tokens.roads, '#123abc');
});

test('precise hex entry rejects invalid values with feedback and safely hydrates only valid URL tokens', async (t) => {
  const creator = await initializedCreator('https://example.test/creator.html#c=123456&w=abcdef&g=bad&r=1234567&b=%3Csvg%3E&t=0f172a');
  t.after(() => creator.close());

  const { document, window, hooks } = creator;
  assert.deepEqual({ ...hooks.tokens }, {
    canvas: '#123456',
    water: '#abcdef',
    greenspace: DEFAULT_TOKENS.greenspace,
    roads: DEFAULT_TOKENS.roads,
    buildings: DEFAULT_TOKENS.buildings,
    text: '#0f172a'
  }, 'only six-digit URL values hydrate; malformed values retain safe defaults');
  assert.equal(inputFor(document, 'canvas').value.toLowerCase(), '#123456', 'hydrated values sync back into cards');
  assert.equal(inputFor(document, 'greenspace').value.toLowerCase(), DEFAULT_TOKENS.greenspace, 'invalid URL values do not leak into inputs');

  const roadsInput = inputFor(document, 'roads');
  const roadsBefore = hooks.tokens.roads;
  dispatchInput(window, roadsInput, 'nope');
  roadsInput.dispatchEvent(new window.Event('blur'));
  assert.equal(hooks.tokens.roads, roadsBefore, 'invalid exact hex never mutates semantic token state');
  assert.equal(roadsInput.getAttribute('aria-invalid'), 'true', 'invalid exact hex has accessible inline feedback');

  dispatchInput(window, roadsInput, '13579b');
  assert.equal(hooks.tokens.roads, '#13579b', 'six-digit shorthand-free hex commits immediately');
  assert.notEqual(roadsInput.getAttribute('aria-invalid'), 'true', 'valid exact hex clears invalid feedback');
});

test('preset application strips display metadata so the wheel has exactly six color pins', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());

  const { document, hooks } = creator;
  const preset = document.querySelector('.preset-pill');
  assert.ok(preset, 'a curated preset is available');
  preset.click();

  assert.deepEqual(Object.keys(hooks.tokens).sort(), [...TOKENS].sort(), 'preset display name/category are excluded from token state');
  for (const color of Object.values(hooks.tokens)) {
    assert.match(color, /^#[0-9a-f]{6}$/i, 'every wheel token is a valid color');
  }

  hooks.setStudioView('wheel');
  assert.equal(document.querySelectorAll('.wheel-pin-group').length, TOKENS.length, 'wheel renders one pin per semantic token, never preset metadata');
});

test('shuffle preserves held tokens, including monochrome generation', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());

  const { hooks } = creator;
  hooks.setTokens({
    canvas: '#f8fafc',
    water: '#0ea5e9',
    greenspace: '#22c55e',
    roads: '#dc2626',
    buildings: '#e2e8f0',
    text: '#0f172a'
  });
  hooks.syncTokenInputs();
  hooks.setHeld({ roads: true, water: false });
  const heldRoads = hooks.tokens.roads;
  hooks.executeHarmoniousShuffle('triadic');
  assert.equal(hooks.tokens.roads, heldRoads, 'a held road token survives ordinary harmony shuffle exactly');

  hooks.setHeld({ roads: false, water: true });
  const heldWater = hooks.tokens.water;
  hooks.executeHarmoniousShuffle('monochrome');
  assert.equal(hooks.tokens.water, heldWater, 'a held token survives monochrome shuffle exactly');
  assert.deepEqual(Object.keys(hooks.tokens).sort(), [...TOKENS].sort(), 'shuffle keeps the state limited to the six semantic tokens');
});

test('bulk controls, projections, and export remain usable immediately after a fast exact edit', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());

  const { document, window, hooks, maps, errors, downloaded } = creator;
  const roadsInput = inputFor(document, 'roads');
  dispatchInput(window, roadsInput, '#102030');
  dispatchInput(window, roadsInput, '#203040');
  assert.equal(hooks.tokens.roads, '#203040', 'the last rapid edit is authoritative');

  document.getElementById('btnAutoContrast').click();
  document.getElementById('btnHarmonize').click();
  document.getElementById('btnProjGlobe').click();
  document.getElementById('btnProjMercator').click();
  document.getElementById('btnDownload').click();

  const map = maps[0];
  assert.ok(map, 'the renderer was initialized through the MapLibre stub');
  assert.ok(map.calls.some(([method, projection]) => method === 'setProjection' && projection.type === 'globe'), '3D projection reaches the renderer');
  assert.ok(map.calls.some(([method, projection]) => method === 'setProjection' && projection.type === 'mercator'), '2D projection reaches the renderer');
  assert.ok(map.calls.some(([method]) => method === 'setStyle'), 'bulk controls compile a new in-memory style');
  assert.ok(hooks.currentStyle?.layers?.length > 0, 'actual BASE_TEMPLATE compiles to an exportable MapLibre style');
  assert.match(document.getElementById('rawJsonCode').textContent, /Custom Basemap/, 'compiled JSON preview updates after bulk actions');
  assert.equal(downloaded.at(-1)?.download, 'custom-map-style.json', 'export creates the expected JSON download');
  assert.deepEqual(errors, [], 'no controller exceptions occur while using controls immediately after editing');
});

test('Advanced preserves palette, holds and its selected view across closing and reopening', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());
  const { document, window, hooks } = creator;
  const advanced = document.getElementById('advancedTools');
  hooks.toggleHold('water');
  const before = { ...hooks.tokens };
  advanced.open = true;
  await new Promise(resolve => window.setTimeout(resolve, 5));
  assert.equal(document.getElementById('colorWheelSection').classList.contains('is-hidden'), false);
  assert.equal(document.getElementById('tokenGrid').classList.contains('is-hidden'), false);
  document.getElementById('tabBtnWheel').click();
  assert.equal(document.getElementById('tokenGrid').classList.contains('is-hidden'), true);
  advanced.open = false;
  await new Promise(resolve => window.setTimeout(resolve, 5));
  assert.equal(document.getElementById('tokenGrid').classList.contains('is-hidden'), false);
  advanced.open = true;
  await new Promise(resolve => window.setTimeout(resolve, 5));
  assert.equal(document.getElementById('tabBtnWheel').getAttribute('aria-pressed'), 'true');
  assert.equal(document.getElementById('tokenGrid').classList.contains('is-hidden'), true);
  assert.deepEqual({ ...hooks.tokens }, before);
  assert.equal(hooks.heldTokens.water, true);
});

test('tonal controls stay hue-preserving and the current chip does not alter the exact colour', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());
  const { document, window, hooks } = creator;
  hooks.onTokenChanged('water', '#b4d4eb');
  document.querySelector('#ladderWater .tonal-chip.active').click();
  assert.equal(hooks.tokens.water, '#b4d4eb');
  const expected = window.StyleEngine.adjustHsl('#b4d4eb', { l: -8 });
  document.querySelector('.btn-tone-step[data-token="water"][data-delta="-8"]').click();
  assert.equal(hooks.tokens.water, expected);
  assert.equal(inputFor(document, 'water').value, expected);
  assert.equal(document.querySelectorAll('#ladderWater .tonal-chip').length, 5);
});

test('all six locks disable shuffle and can be released, while manual colour changes still work', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());
  const { document, hooks } = creator;
  TOKENS.forEach(key => hooks.toggleHold(key));
  const before = { ...hooks.tokens };
  assert.equal(document.getElementById('btnShuffle').disabled, true);
  hooks.executeHarmoniousShuffle('triadic');
  assert.deepEqual({ ...hooks.tokens }, before);
  hooks.onTokenChanged('water', '#123456');
  assert.equal(hooks.tokens.water, '#123456');
  document.getElementById('btnClearHolds').click();
  assert.equal(document.getElementById('btnShuffle').disabled, false);
  assert.ok(Object.values(hooks.heldTokens).every(value => value === false));
});

test('sharing and JSON export use the latest palette without waiting for the edit debounce', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());
  const { document, window, hooks } = creator;
  const copied = [];
  window.navigator.clipboard.writeText = async value => { copied.push(value); };
  dispatchInput(window, inputFor(document, 'water'), '#abcdef');
  document.getElementById('btnShare').click();
  assert.match(copied[0], /w=abcdef/);
  document.getElementById('btnDownload').click();
  const expected = window.StyleEngine.compileMapLibreStyle(window.BASE_TEMPLATE, window.StyleEngine.generateThemeConfig(hooks.tokens));
  assert.equal(JSON.stringify(hooks.currentStyle), JSON.stringify(expected));
  document.getElementById('btnInspect').click();
  assert.equal(document.getElementById('inspectorDrawer').classList.contains('open'), true);
  document.getElementById('btnCopyJson').click();
  assert.equal(copied.at(-1), JSON.stringify(expected, null, 2));
  document.getElementById('btnCloseInspector').click();
  assert.equal(document.getElementById('btnInspect').getAttribute('aria-expanded'), 'false');
});

test('wheel dragging after preset selection keeps six valid colours and preserves held pins', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());
  const { document, window, hooks } = creator;
  document.querySelectorAll('.preset-pill')[2].click();
  hooks.toggleHold('water');
  const water = hooks.tokens.water;
  hooks.setStudioView('both');
  const svg = document.getElementById('colorWheelSvg');
  let capturedPointer;
  svg.setPointerCapture = pointerId => { capturedPointer = pointerId; };
  const pin = svg.querySelector('.wheel-pin-group[data-token="roads"]');
  const down = new window.MouseEvent('pointerdown', { bubbles: true });
  Object.defineProperty(down, 'pointerId', { value: 4 });
  pin.dispatchEvent(down);
  svg.dispatchEvent(new window.MouseEvent('pointermove', { bubbles: true, clientX: 130, clientY: 240 }));
  svg.dispatchEvent(new window.MouseEvent('pointerup', { bubbles: true }));
  assert.equal(capturedPointer, 4, 'the persistent SVG captures drag events, not a replaced pin');
  assert.equal(hooks.tokens.water, water);
  assert.equal(Object.keys(hooks.tokens).length, 6);
  Object.values(hooks.tokens).forEach(value => assert.match(value, /^#[0-9a-f]{6}$/));
  TOKENS.forEach(key => assert.equal(inputFor(document, key).value, hooks.tokens[key]));
});

test('all harmony choices, light/dark conversion, wheel lightness and location presets remain connected', async (t) => {
  const creator = await initializedCreator();
  t.after(() => creator.close());
  const { document, window, hooks } = creator;
  const harmony = document.getElementById('selectHarmony');
  for (const option of harmony.options) {
    harmony.value = option.value;
    harmony.dispatchEvent(new window.Event('change'));
    document.getElementById('btnHarmonize').click();
    assert.equal(Object.keys(hooks.tokens).length, 6);
    Object.values(hooks.tokens).forEach(value => assert.match(value, /^#[0-9a-f]{6}$/));
  }
  document.getElementById('btnModeDark').click();
  assert.equal(document.getElementById('btnModeDark').getAttribute('aria-pressed'), 'true');
  document.getElementById('btnModeLight').click();
  assert.equal(document.getElementById('btnModeLight').getAttribute('aria-pressed'), 'true');
  hooks.selectWheelToken('water');
  const slider = document.getElementById('wheelLightnessSlider');
  slider.value = '42';
  slider.dispatchEvent(new window.Event('input'));
  assert.equal(inputFor(document, 'water').value, hooks.tokens.water);
  assert.equal(document.getElementById('activeTokenHex').textContent, hooks.tokens.water);
  const location = document.getElementById('locationSelect');
  location.value = 'tokyo';
  location.dispatchEvent(new window.Event('change'));
  assert.ok(hooks.map.calls.some(([method, options]) => method === 'flyTo' && options.center[0] === 139.6917));
});
