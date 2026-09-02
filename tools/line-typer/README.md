# Line Typer

A small Chrome/Edge extension (Manifest V3) that types saved text into the
field you have focused, one line or one keystroke at a time, instead of
dropping it in as a single paste.

Built from scratch here - no store extension, no account, no quota, nothing
leaves the browser. The text lives in `chrome.storage.local` on your machine.

## Install

1. Open `chrome://extensions`.
2. Turn on **Developer mode** (top right).
3. Click **Load unpacked** and pick this `line-typer` folder.
4. Pin the extension so the toolbar icon is visible.

## Use it

1. Click the toolbar icon, paste your text, pick a preset.
2. Click into the box you want the text to go into - **the extension types
   wherever the cursor is blinking**. There is no target picker; focus is the
   target. This is also why "no editable element focused" happens: the click
   landed on the panel instead of the page.
3. Press **Ctrl+Shift+Y** (Cmd+Shift+Y on Mac).

The popup's **Type now** button works too: it gives you a 3 second countdown to
click into the box before typing starts, because opening the popup takes focus
away from the page. The keyboard shortcut has no such problem, so it is the
reliable one.

Stop any time with **Esc**, **Ctrl+Shift+X**, or the Stop button on the
on-page indicator.

## New line behaviour

This is the setting that matters most, because "new line" means different
things in different boxes:

| Mode | What it sends | Use for |
| --- | --- | --- |
| `Shift+Enter` | line break inside the current message | WhatsApp Web, Slack, Discord - one multi-line message |
| `Enter` | submits the line | WhatsApp Web when you want each line as its own message |
| `Insert \n` | a real newline character | textareas, code editors (CodeMirror, Monaco, Ace) |

A plain `<textarea>` or `<input>` has no JavaScript listening for Enter, and a
synthetic key press does not trigger the browser's own default action there.
So for those the extension forces `Insert \n` no matter what is selected -
otherwise everything would silently land on one line.

## Options

- **Style** - `Line by line` (default), `Human typing` (per-keystroke, with
  variable pacing), or `All at once`.
- **Speed / Line pause / Randomness** - timing controls.
- **Strip indentation** - drops leading whitespace per line, for code editors
  that auto-indent and would otherwise double your indentation.

## Limits worth knowing

- Works on **web.whatsapp.com** in the browser. It cannot reach the WhatsApp
  *desktop app* - that is a native window, not a web page, and no browser
  extension can type into it.
- Does not run on `chrome://` pages, the Chrome Web Store, or the built-in PDF
  viewer. Chrome blocks extensions there.
- On `file://` pages you must tick "Allow access to file URLs" in the
  extension's details page.
- It never sends a message on its own. In `Shift+Enter` mode the text is left
  sitting in the composer for you to read and press Enter yourself.

## Layout

| File | Role |
| --- | --- |
| `manifest.json` | permissions, content script registration, keyboard shortcuts |
| `content.js` | the typing engine, target detection, on-page indicator |
| `background.js` | service worker; routes the keyboard shortcuts to the page |
| `popup.html/.css/.js` | the control panel |
| `defaults.js` | shared default settings |
