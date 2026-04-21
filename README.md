# SmartEmoji

A tiny, fast, minimal emoji picker for Windows. Press a hotkey, type to search, press Enter — the emoji is typed straight into whatever app you were in.

![SmartEmoji popup](https://raw.githubusercontent.com/Claxon/SmartEmoji/main/.github/screenshot.png)

## What it does

- **Global hotkey** (default `Ctrl+;`, configurable, multiple hotkeys allowed) opens a picker next to your text caret.
- **Search by name, shortcode, or keyword** — typing `heart`, `party`, or `rofl` filters instantly.
- **Most-used first** — a 14-day time-decayed score floats your recent picks to the top.
- **Custom shortcodes** — map any text (`shrug`, `hbd`, whatever) to any Unicode emoji.
- **Custom image "emojis"** — drop in your own PNGs and paste them as images into Word/Outlook/Slack/Discord/etc.
- **Clipboard-safe.** Unicode emojis are typed directly via the Windows `KEYEVENTF_UNICODE` keystroke — your clipboard is never touched. Image pastes restore your clipboard immediately after.
- **Under 1 MB of user-visible data**, a single portable .exe, and it lives quietly in the tray.

## Install

### Option A — portable exe

1. Grab `SmartEmoji.exe` from the [latest release](https://github.com/Claxon/SmartEmoji/releases/latest).
2. Put it anywhere you like. Double-click it.
3. A tray icon appears. Right-click it → **Run at startup** if you want it every login.

Nothing to install, no admin rights, no telemetry.

### Option B — run from source

Requires Python 3.11+ on Windows.

```
git clone https://github.com/Claxon/SmartEmoji.git
cd SmartEmoji
install.bat   # creates .venv, installs PySide6
run.bat       # starts the app (no console window)
```

## Using it

| Action | Key |
|---|---|
| Open picker | `Ctrl+;` (configurable) |
| Search | just type |
| Move selection | ←/→/↑/↓ or Tab |
| Insert emoji | Enter or click |
| Cancel | Esc, or click outside the popup |

Right-click the tray icon → **Settings…** for:

- **Hotkeys** — add/remove any Ctrl/Alt/Shift/Win + key combination.
- **Shortcodes** — map your own text to a Unicode emoji (e.g. `party` → 🎉).
- **Images** — add your own PNGs/JPGs/GIFs as searchable image emojis.
- **General** — grid columns, grid rows (go down to 1 for a single-row compact picker), toggle the name/shortcode caption, toggle "Run at startup".

## How it types

Unlike emoji pickers that always paste via Ctrl+V, SmartEmoji types each Unicode emoji as a `KEYEVENTF_UNICODE` keystroke — the same mechanism Windows uses for dead-keys and IME. Three consequences:

1. Your clipboard stays untouched.
2. It works in edit controls that re-select their contents on focus (URL bars, search boxes) — Ctrl+V paste tools overwrite those selections; `KEYEVENTF_UNICODE` just appends at the caret.
3. Emojis outside the Basic Multilingual Plane (most of them) are sent as UTF-16 surrogate pairs, which is what Windows expects.

Image emojis are the exception — images have to go through the clipboard, but the previous clipboard contents are snapshotted first and restored after a short delay.

## Build your own exe

```
pip install pyinstaller
pyinstaller --onefile --windowed --noconfirm --name SmartEmoji ^
    --add-data "assets/emojis.json;assets" main.py
```

Output: `dist/SmartEmoji.exe`.

## Refresh the emoji dataset

The bundled dataset is derived from [muan/emojilib](https://github.com/muan/emojilib) and covers ~1850 Unicode emojis.

```
python scripts/build_emojis.py
```

Fetches the latest emojilib data, re-ranks by a hand-curated popularity list, writes `assets/emojis.json`.

## Why

Windows has a built-in picker at `Win+.` but it's slow, loses your selection every time, doesn't support custom shortcodes, can't hold your own images, and can't be rebound. SmartEmoji is ~1500 lines of Python that fixes all of those.

## License

MIT.
