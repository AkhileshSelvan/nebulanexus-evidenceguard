/* Line Typer - service worker. Relays keyboard shortcuts to the page. */
importScripts('defaults.js');

async function config() {
  const stored = await chrome.storage.local.get(LT_DEFAULTS);
  return { ...LT_DEFAULTS, ...stored };
}

async function activeTabId() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab && tab.id;
}

chrome.commands.onCommand.addListener(async (command) => {
  const tabId = await activeTabId();
  if (!tabId) return;
  try {
    if (command === 'type-now') {
      const cfg = await config();
      // Shortcut path: focus is already where the user wants it, so no countdown.
      await chrome.tabs.sendMessage(tabId, { type: 'START', config: { ...cfg, countdown: 0 } });
    } else if (command === 'stop-typing') {
      await chrome.tabs.sendMessage(tabId, { type: 'STOP' });
    }
  } catch (err) {
    // No content script on this page (chrome://, the Web Store, a PDF viewer).
    console.warn('Line Typer:', err.message);
  }
});
