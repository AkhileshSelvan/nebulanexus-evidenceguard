/* Shared defaults. Loaded by the popup and imported by the service worker. */
const LT_DEFAULTS = {
  text: '',
  mode: 'line',       // line | human | instant
  charDelay: 45,      // ms between keystrokes (human mode)
  lineDelay: 220,     // ms at each line break
  jitter: 45,         // +/- % randomness on every delay
  pauseChance: 0.02,  // chance per character of a "thinking" pause
  pauseMs: 400,       // length of that pause
  typoChance: 0,      // chance per letter of a typo + backspace
  stripIndent: false, // let the editor auto-indent instead of typing spaces
  newline: 'shift',   // shift (Shift+Enter) | key (Enter) | insert (\n)
  countdown: 3        // seconds to click into the editor (popup start only)
};

if (typeof module !== 'undefined') module.exports = { LT_DEFAULTS };
