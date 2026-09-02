/* Line Typer - content script.
 * Inserts saved text into whatever editable element currently has focus,
 * one line (or one character) at a time.
 */
(() => {
  if (window.__lineTyperLoaded) return;
  window.__lineTyperLoaded = true;

  const state = { running: false, abort: false, hud: null, shadow: null };

  /* ---------------------------------------------------------------- target */

  const TEXT_INPUT = /^(text|search|url|email|tel|password|number|)$/i;

  function findTarget() {
    let el = document.activeElement;
    // Walk into open shadow roots (Monaco/CodeMirror inside web components).
    while (el && el.shadowRoot && el.shadowRoot.activeElement) {
      el = el.shadowRoot.activeElement;
    }
    if (!el || el === document.body || el === document.documentElement) return null;
    if (el.closest && el.closest('[data-line-typer-hud]')) return null;
    if (el.tagName === 'TEXTAREA') return el;
    if (el.tagName === 'INPUT' && TEXT_INPUT.test(el.type || '')) return el;
    if (el.isContentEditable) return el;
    return null;
  }

  /* -------------------------------------------------------------- insertion */

  function insert(el, str) {
    if (!str) return true;
    if (document.activeElement !== el) {
      try { el.focus({ preventScroll: false }); } catch (_) { /* ignore */ }
    }
    // execCommand is the only insertion path that CodeMirror, Monaco and Ace
    // all pick up, because it fires a real beforeinput/input pair.
    try {
      if (document.execCommand('insertText', false, str)) return true;
    } catch (_) { /* fall through */ }

    if ('value' in el && typeof el.selectionStart === 'number') {
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const next = el.value.slice(0, start) + str + el.value.slice(end);
      const setter = Object.getOwnPropertyDescriptor(
        Object.getPrototypeOf(el), 'value'
      );
      if (setter && setter.set) setter.set.call(el, next);
      else el.value = next;
      el.selectionStart = el.selectionEnd = start + str.length;
      el.dispatchEvent(new InputEvent('input', {
        bubbles: true, inputType: 'insertText', data: str
      }));
      return true;
    }

    if (el.isContentEditable) {
      const sel = window.getSelection();
      if (sel && sel.rangeCount) {
        const range = sel.getRangeAt(0);
        range.deleteContents();
        const node = document.createTextNode(str);
        range.insertNode(node);
        range.setStartAfter(node);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
        el.dispatchEvent(new InputEvent('input', {
          bubbles: true, inputType: 'insertText', data: str
        }));
        return true;
      }
    }
    return false;
  }

  function pressEnter(el, shift) {
    const init = {
      key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
      shiftKey: !!shift, bubbles: true, cancelable: true, composed: true
    };
    el.dispatchEvent(new KeyboardEvent('keydown', init));
    el.dispatchEvent(new KeyboardEvent('keypress', init));
    el.dispatchEvent(new KeyboardEvent('keyup', init));
  }

  // How a line break is produced depends on the target:
  //   insert - put a real \n in the text (plain textareas, code editors)
  //   shift  - Shift+Enter, a line break inside one WhatsApp message
  //   key    - plain Enter, which in WhatsApp sends the message
  function newline(el, mode) {
    if (mode === 'key') pressEnter(el, false);
    else if (mode === 'shift') pressEnter(el, true);
    else insert(el, '\n');
  }

  /* -------------------------------------------------------------------- HUD */

  function hud() {
    if (state.hud) return state.hud;
    const host = document.createElement('div');
    host.setAttribute('data-line-typer-hud', '');
    host.style.cssText = 'all:initial;position:fixed;z-index:2147483647;right:16px;bottom:16px;';
    const shadow = host.attachShadow({ mode: 'closed' });
    shadow.innerHTML = `
      <style>
        .box{font:13px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
             background:#14161a;color:#e8eaed;border:1px solid #2f333a;border-radius:10px;
             padding:10px 12px;box-shadow:0 6px 24px rgba(0,0,0,.35);min-width:190px}
        .row{display:flex;align-items:center;justify-content:space-between;gap:10px}
        .label{font-weight:600}
        .hint{color:#9aa0a6;font-size:11px;margin-top:6px}
        .bar{height:4px;background:#2f333a;border-radius:2px;margin-top:8px;overflow:hidden}
        .fill{height:100%;width:0;background:#7cc4ff;transition:width .08s linear}
        button{font:inherit;background:#2f333a;color:#e8eaed;border:0;border-radius:6px;
               padding:3px 9px;cursor:pointer}
        button:hover{background:#3c4149}
      </style>
      <div class="box">
        <div class="row"><span class="label"></span><button type="button">Stop</button></div>
        <div class="bar"><div class="fill"></div></div>
        <div class="hint">Esc or Ctrl+Shift+X to stop</div>
      </div>`;
    shadow.querySelector('button').addEventListener('click', () => stop('Stopped'));
    (document.body || document.documentElement).appendChild(host);
    state.hud = host;
    state.shadow = shadow;
    return host;
  }

  function say(text, done, total) {
    hud();
    state.shadow.querySelector('.label').textContent = text;
    const pct = total ? Math.round((done / total) * 100) : 0;
    state.shadow.querySelector('.fill').style.width = pct + '%';
  }

  function hideHud(delay = 1200) {
    setTimeout(() => {
      if (state.running) return;
      if (state.hud) state.hud.remove();
      state.hud = null;
      state.shadow = null;
    }, delay);
  }

  /* ------------------------------------------------------------------- run */

  const sleep = (ms) => new Promise((r) => setTimeout(r, Math.max(0, ms)));

  function jitter(ms, pct) {
    if (!pct) return ms;
    const spread = ms * (pct / 100);
    return Math.max(0, ms + (Math.random() * 2 - 1) * spread);
  }

  // Rough model of how a person actually types code: the gap between two
  // keystrokes is not constant. Symbols and shifted characters are slower,
  // repeated letters inside a word are faster, and every so often the typist
  // stops to think.
  const SLOW_AFTER = /[;{}()\[\]<>"'`=+*/%&|!?:,.]/;
  const SHIFTED = /[A-Z{}()\[\]<>"~!@#$%^&*_+|:?]/;

  function charDelayFor(ch, prev, cfg) {
    let ms = cfg.charDelay;
    if (ch === ' ') ms *= 0.7;                 // space bar is quick
    else if (SHIFTED.test(ch)) ms *= 1.45;     // needs the shift key
    else if (/[0-9]/.test(ch)) ms *= 1.25;     // number row
    if (prev && SLOW_AFTER.test(prev)) ms *= 1.3;
    if (Math.random() < cfg.pauseChance) {
      ms += cfg.pauseMs * (0.5 + Math.random());  // a beat to think
    }
    return jitter(ms, cfg.jitter);
  }

  // Type a character, occasionally fumbling it first and correcting.
  async function humanChar(el, ch, cfg) {
    if (cfg.typoChance > 0 && /[a-z]/i.test(ch) && Math.random() < cfg.typoChance) {
      const neighbours = KEY_NEIGHBOURS[ch.toLowerCase()];
      if (neighbours) {
        const wrong = neighbours[Math.floor(Math.random() * neighbours.length)];
        insert(el, ch === ch.toUpperCase() ? wrong.toUpperCase() : wrong);
        await sleep(jitter(cfg.charDelay * 2.2, cfg.jitter));
        backspace(el);
        await sleep(jitter(cfg.charDelay * 1.8, cfg.jitter));
      }
    }
    insert(el, ch);
  }

  const KEY_NEIGHBOURS = {
    a: 'sqw', b: 'vgn', c: 'xvd', d: 'sfe', e: 'wrd', f: 'dgr', g: 'fht',
    h: 'gjy', i: 'uok', j: 'hku', k: 'jli', l: 'kop', m: 'nj', n: 'bmh',
    o: 'ipl', p: 'ol', q: 'wa', r: 'etf', s: 'adw', t: 'ryg', u: 'yij',
    v: 'cbf', w: 'qes', x: 'zcs', y: 'tuh', z: 'xa'
  };

  function backspace(el) {
    try {
      if (document.execCommand('delete', false)) return true;
    } catch (_) { /* fall through */ }
    if ('value' in el && typeof el.selectionStart === 'number' && el.selectionStart > 0) {
      const at = el.selectionStart;
      const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
      const next = el.value.slice(0, at - 1) + el.value.slice(el.selectionEnd);
      if (setter && setter.set) setter.set.call(el, next);
      else el.value = next;
      el.selectionStart = el.selectionEnd = at - 1;
      el.dispatchEvent(new InputEvent('input', {
        bubbles: true, inputType: 'deleteContentBackward'
      }));
      return true;
    }
    return false;
  }

  function onKeydown(e) {
    if (e.key === 'Escape' && state.running) stop('Stopped');
  }

  function stop(reason) {
    if (!state.running) return;
    state.abort = true;
    state.running = false;
    say(reason || 'Stopped');
    hideHud();
  }

  const DEFAULTS = {
    mode: 'line', charDelay: 45, lineDelay: 220, jitter: 45,
    pauseChance: 0.02, pauseMs: 400, typoChance: 0,
    stripIndent: false, newline: 'shift', countdown: 0
  };

  async function start(options) {
    if (state.running) return { ok: false, error: 'already running' };
    const cfg = { ...DEFAULTS, ...options };
    const text = String(cfg.text || '').replace(/\r\n?/g, '\n');
    if (!text.trim()) return { ok: false, error: 'nothing saved to type' };

    if (cfg.countdown > 0) {
      state.running = true;
      state.abort = false;
      window.addEventListener('keydown', onKeydown, true);
      for (let s = cfg.countdown; s > 0; s--) {
        if (state.abort) { cleanup(); return { ok: false, error: 'cancelled' }; }
        say(`Click the editor... ${s}`);
        await sleep(1000);
      }
      state.running = false;
    }

    const target = findTarget();
    if (!target) {
      say('Click inside the editor first');
      hideHud(2200);
      cleanup();
      return { ok: false, error: 'no editable element focused' };
    }

    // A plain textarea/input has no JavaScript listening for Enter, and a
    // synthetic key press does not trigger the browser's own default action.
    // Only a real "\n" produces a line break there, whatever the user picked.
    if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT') {
      cfg.newline = 'insert';
    }

    state.running = true;
    state.abort = false;
    window.addEventListener('keydown', onKeydown, true);

    const lines = text.split('\n');
    const total = lines.length;
    try {
      if (cfg.mode === 'instant') {
        say('Typing...', 0, total);
        insert(target, cfg.stripIndent ? lines.map(stripOne).join('\n') : text);
        say(`Done - ${total} lines`, total, total);
      } else {
        for (let i = 0; i < total; i++) {
          if (state.abort) break;
          const line = cfg.stripIndent ? stripOne(lines[i]) : lines[i];

          if (i > 0) {
            newline(target, cfg.newline);
            // A person pauses a little longer at the end of a line, and
            // longer still after a blank line or a closing brace.
            let pause = cfg.lineDelay;
            const prevLine = lines[i - 1].trim();
            if (prevLine === '' || prevLine === '}' || prevLine.endsWith('{')) pause *= 1.6;
            await sleep(jitter(pause, cfg.jitter));
          }
          if (state.abort) break;

          if (cfg.mode === 'line') {
            insert(target, line);
          } else {
            let prev = '';
            for (const ch of line) {
              if (state.abort) break;
              await humanChar(target, ch, cfg);
              await sleep(charDelayFor(ch, prev, cfg));
              prev = ch;
            }
          }
          say(`Typing ${i + 1}/${total}`, i + 1, total);
        }
        if (!state.abort) say(`Done - ${total} lines`, total, total);
      }
    } finally {
      const aborted = state.abort;
      cleanup();
      hideHud(aborted ? 900 : 1600);
      return { ok: !aborted, lines: total };
    }
  }

  function stripOne(line) {
    return line.replace(/^[ \t]+/, '');
  }

  function cleanup() {
    state.running = false;
    state.abort = false;
    window.removeEventListener('keydown', onKeydown, true);
  }

  /* -------------------------------------------------------------- messaging */

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (!msg || !msg.type) return;
    if (msg.type === 'PING') {
      // Only the frame that actually holds an editable focus answers.
      const target = findTarget();
      sendResponse({ editable: !!target, tag: target ? target.tagName : null });
      return;
    }
    if (msg.type === 'STOP') {
      stop('Stopped');
      sendResponse({ ok: true });
      return;
    }
    if (msg.type === 'START') {
      // Frames without focus stay silent so the focused one wins.
      if (!(msg.config && msg.config.countdown > 0) && !findTarget()) {
        sendResponse({ ok: false, error: 'not focused here' });
        return;
      }
      start(msg.config).then(sendResponse);
      return true; // async response
    }
  });

  window.__lineTyperStop = () => stop('Stopped');
})();
