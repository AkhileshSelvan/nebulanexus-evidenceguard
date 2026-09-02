/* Line Typer - popup controller. */
const $ = (id) => document.getElementById(id);
const els = {
  text: $('text'), mode: $('mode'), speed: $('speed'), lineDelay: $('lineDelay'),
  jitter: $('jitter'), stripIndent: $('stripIndent'), typo: $('typo'),
  newline: $('newline'), start: $('start'), stop: $('stop'),
  status: $('status'), meta: $('meta'),
  presetWhatsapp: $('presetWhatsapp'), presetEditor: $('presetEditor')
};

// Sensible starting points for the two things people actually paste into.
const PRESETS = {
  whatsapp: { mode: 'line', newline: 'shift', lineDelay: 150, jitter: 30,
              stripIndent: false, typoChance: 0 },
  editor:   { mode: 'line', newline: 'insert', lineDelay: 200, jitter: 30,
              stripIndent: false, typoChance: 0 }
};

const TYPO_ON = 0.03;

function nearestSpeed(value) {
  const options = [...els.speed.options].map((o) => Number(o.value));
  return String(options.reduce((a, b) => (Math.abs(b - value) < Math.abs(a - value) ? b : a)));
}

async function load() {
  const cfg = { ...LT_DEFAULTS, ...(await chrome.storage.local.get(LT_DEFAULTS)) };
  els.text.value = cfg.text;
  els.mode.value = cfg.mode;
  els.speed.value = nearestSpeed(cfg.charDelay);
  els.lineDelay.value = cfg.lineDelay;
  els.jitter.value = cfg.jitter;
  els.stripIndent.checked = cfg.stripIndent;
  els.typo.checked = cfg.typoChance > 0;
  els.newline.value = cfg.newline;
  syncMode();
  count();
}

function read() {
  return {
    text: els.text.value,
    mode: els.mode.value,
    charDelay: Number(els.speed.value),
    lineDelay: Number(els.lineDelay.value) || 0,
    jitter: Number(els.jitter.value) || 0,
    pauseChance: LT_DEFAULTS.pauseChance,
    pauseMs: LT_DEFAULTS.pauseMs,
    typoChance: els.typo.checked ? TYPO_ON : 0,
    stripIndent: els.stripIndent.checked,
    newline: els.newline.value,
    countdown: LT_DEFAULTS.countdown
  };
}

const save = () => chrome.storage.local.set(read());

function count() {
  const lines = els.text.value ? els.text.value.split('\n').length : 0;
  const chars = els.text.value.length;
  els.meta.textContent = lines ? `${lines} lines / ${chars} chars` : '';
}

function syncMode() {
  const human = els.mode.value === 'human';
  els.speed.disabled = !human;
  els.typo.disabled = !human;
  els.lineDelay.disabled = els.mode.value === 'instant';
  // "All at once" cannot use key presses for line breaks - there is no
  // per-line step to press a key in.
  const instant = els.mode.value === 'instant';
  if (instant && els.newline.value !== 'insert') els.newline.value = 'insert';
  els.newline.disabled = instant;
  els.status.textContent = els.newline.value === 'key'
    ? 'Each line is sent as its own message.'
    : 'Click the message box, then Ctrl+Shift+Y.';
  els.status.classList.remove('error');
}

function applyPreset(name) {
  const p = PRESETS[name];
  els.mode.value = p.mode;
  els.newline.value = p.newline;
  els.lineDelay.value = p.lineDelay;
  els.jitter.value = p.jitter;
  els.stripIndent.checked = p.stripIndent;
  els.typo.checked = p.typoChance > 0;
  syncMode();
  save();
}

function status(text, isError) {
  els.status.textContent = text;
  els.status.classList.toggle('error', !!isError);
}

async function send(message) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) throw new Error('no active tab');
  return chrome.tabs.sendMessage(tab.id, message);
}

els.start.addEventListener('click', async () => {
  await save();
  const cfg = read();
  if (!cfg.text.trim()) return status('Paste something first.', true);
  try {
    // Fire and forget: the countdown runs in the page so the popup can close
    // and the user can click into the editor.
    send({ type: 'START', config: cfg }).catch(() => {});
    setTimeout(() => window.close(), 80);
  } catch (err) {
    status('This page does not allow extensions.', true);
  }
});

els.stop.addEventListener('click', async () => {
  try {
    await send({ type: 'STOP' });
    status('Stopped.');
  } catch (err) {
    status('Nothing running here.', true);
  }
});

els.presetWhatsapp.addEventListener('click', () => applyPreset('whatsapp'));
els.presetEditor.addEventListener('click', () => applyPreset('editor'));

for (const el of [els.mode, els.speed, els.lineDelay, els.jitter,
                  els.stripIndent, els.typo, els.newline]) {
  el.addEventListener('change', () => { syncMode(); save(); });
}
els.text.addEventListener('input', () => { count(); save(); });

load();
