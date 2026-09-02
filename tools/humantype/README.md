# humantype

Copy code. Run `humantype`. It types the code into whatever window you click
into — character by character, at a human rhythm — instead of pasting it.

Because it sends real OS-level key events, the target does not have to
cooperate: it works in a browser field, a code editor, a terminal, a VNC or
IPMI console, a VM window, anything that takes a keyboard.

```console
$ humantype --file solution.py --indent reset
  cleaned: expanded 12 tab(s) to spaces
331 keystrokes over 18 line(s) -- about 6.2s.
Typing in 5... (click into the target field now)
...
Done -- 331 keystrokes sent.
```

## Why not just paste?

Plenty of places where a paste is unavailable or unhelpful:

- **Remote consoles** — VNC, IPMI/iDRAC, hypervisor consoles and many SSH-in-
  browser clients share no clipboard with your machine. Typing is the only
  channel there.
- **Screencasts and live demos** — code that appears instantly reads as a jump
  cut. Code that types reads as a demo.
- **Fields that mangle a paste** — editors that auto-indent turn a pasted block
  into a staircase; `humantype --indent reset` fixes that at the source.
- **Auto-type in the KeePass sense** — filling a field on a machine where the
  clipboard is shared, logged, or scraped.

If a site deliberately blocks paste as part of a proctored or invigilated
exam, typing around that block is cheating. That is on you, not the tool.

## Install

The planner, the test suite and `--dry-run` need nothing but Python 3.10+.
To actually press keys you need a backend:

```bash
cd tools/humantype
python3 -m pip install -e ".[keyboard]"
```

That pulls in pynput (keys) and pyperclip (clipboard). Use `python3 -m pip`
rather than a bare `pip`: on macOS and many Linux setups `pip` is not on PATH
even though Python is, and `python3 -m pip` always targets the interpreter
that will actually run the tool.

Linux without pynput: `sudo apt install xdotool` works as a fallback, and
`xclip`/`wl-paste` cover the clipboard.

| Platform | Backend | Notes |
| --- | --- | --- |
| Windows | pynput | works out of the box |
| macOS | pynput | needs Accessibility permission for your terminal |
| Linux (X11) | pynput or xdotool | either |
| Linux (Wayland) | — | no global key injection; use a VM/X11 session |

## Use

```bash
humantype                              # type the clipboard after a 5s countdown
humantype --file main.py               # type a file
cat main.py | humantype --stdin        # type whatever is piped in
humantype --text 'SELECT 1;'           # type a literal string

humantype --dry-run                    # print the plan, press nothing
humantype --preview                    # just report size and duration
```

The countdown is the whole interface: start it, then click into the target
field. Whatever has focus when it ends gets typed into. `Ctrl+C` aborts
mid-type (the field keeps the partial text).

To skip the countdown entirely, run it as a daemon and trigger it from
wherever your cursor already is:

```bash
humantype --hotkey '<ctrl>+<alt>+v' --indent reset
```

### Indentation

The one setting worth understanding. Code editors indent for you, so typing
already-indented code line by line produces a staircase.

| `--indent` | Behaviour | Use for |
| --- | --- | --- |
| `literal` (default) | Types the text exactly as-is | `<textarea>`, terminals, plain forms |
| `reset` | Selects to the line start after each newline, so the first typed character overwrites whatever the editor auto-inserted | VS Code, IntelliJ, CodeMirror, Monaco |
| `strip` | Sends no leading whitespace; lets the editor indent | Editors whose auto-indent you trust |

`reset` is safe even when the editor did nothing — the selection is simply
empty and the character inserts normally.

### Rhythm

```bash
humantype --profile natural            # a plausible working developer
humantype --profile demo               # slow enough to follow on video
humantype --profile careful --typos 0.01   # hesitant, with corrected slips
humantype --wpm 300 --jitter 0.4       # or set it directly
humantype --seed 42                    # same rhythm every run
```

| Profile | WPM | Character |
| --- | --- | --- |
| `fast` (default) | 320 | quick and even |
| `natural` | 210 | uneven, occasional pauses |
| `careful` | 140 | hesitant, optional typos |
| `demo` | 95 | long pauses at line breaks |
| `robot` | 600 | metronomic; for debugging |

Timing is not a flat delay with noise bolted on. Per character it accounts
for: awkward keys (symbols and the number row are slower), repeated
characters (faster), leading indentation (much faster), a longer breath after
a line that opens or closes a block, and an occasional mid-line pause.
Spacing is drawn from a log-normal distribution, which is the shape real
inter-keystroke intervals have — and never goes negative.

### Text cleanup

Clipboard content from a rendered web page is rarely clean. Before typing,
`humantype` reports and fixes what would otherwise break the paste:

- **CRLF** → LF, so you don't get doubled newlines.
- **Tabs** → spaces to the next tab stop. A raw Tab in a browser moves focus
  out of the field, so tabs are never sent as keystrokes.
- **Non-breaking and exotic spaces** → real spaces. These are invisible and
  break compilers.
- **Smart quotes and en/em dashes** → ASCII. Disable with `--keep-smart-quotes`.
- **Zero-width and directional marks** → removed.
- **Trailing whitespace** → stripped. Keep it with `--keep-trailing`.

Characters your keyboard layout probably cannot produce (anything outside
Basic Latin) are warned about up front rather than silently dropped mid-type.

## How it works

```
text ──▶ text.normalise ──▶ planner.plan ──▶ runner.run ──▶ driver
         (fix hazards)      (pure: keys      (sleeps in     (presses
                             + delays)        real time)     keys)
```

The split is the point. `plan()` is pure and deterministic given a seed, so
the interesting behaviour — the rhythm, the indent handling, the typo
correction — is unit-testable without a display, a clipboard, or a focused
window. `transcript()` replays a plan through a model of a real text field
(backspace deletes, `shift+Home` selects to line start) and reconstructs the
resulting text, so a test can assert that a plan reproduces its input exactly.

| Module | Role |
| --- | --- |
| `profile.py` | Timing profiles and `IndentMode` |
| `text.py` | Normalisation and hazard reporting |
| `planner.py` | Pure text → `[Keystroke]`, plus `transcript()` |
| `runner.py` | Replays a plan in real time; injectable clock |
| `drivers.py` | pynput / xdotool / dry-run backends |
| `clipboard.py` | Clipboard reads, with per-platform fallbacks |
| `cli.py` | Argument parsing and wiring |

## Tests

```bash
./run_tests.sh
```

89 tests, standard library only — no pytest, no display, no network.
`SyntaxWarning` is promoted to an error, so an invalid escape sequence
fails the suite instead of merely warning on every import.

## Known limits

- **Wayland** blocks global key injection by design; there is no workaround
  from userspace.
- **Auto-closing brackets** — editors that insert a closing `)` or `"` for you
  usually let the matching typed character type over it, so code arrives
  intact. If yours doesn't, turn the feature off for the paste.
- **Keyboard layout** — the driver types characters your layout can produce.
  On a non-US layout, exotic symbols may not land; `--dry-run` plus the
  warning tells you before you commit to a long type.
- **Speed** — above roughly 600 WPM some fields drop characters. The default
  leaves plenty of headroom.
