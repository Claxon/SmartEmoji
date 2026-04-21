# SmartEmoji — notes for Claude

A lightweight Windows tray app that pops up an emoji picker at the text caret on a hotkey, types the emoji directly into the focused app, and lets the user extend it with custom shortcodes and pasteable images.

## What this app actually does, mechanically

1. `main.py` boots a `QApplication`, spins up a tray icon, and launches a worker thread that owns the Win32 `RegisterHotKey` message loop (`src/hotkeys.py`).
2. When the hotkey fires, the worker thread emits a Qt signal; on the GUI thread, `EmojiPopup.show_at_caret()`:
   - records the currently-foreground HWND so we can restore focus later
   - places the frameless popup next to the caret using `GetGUIThreadInfo` (caret) → `GetCursorPos` → window-centre fallback, all in `src/foreground.py`
   - focuses the search `QLineEdit`
3. User types (filters the grid), arrows (moves selection), Enter (confirms).
4. On confirm:
   - **Unicode emoji** → skip the clipboard, type the character directly via `SendInput` with `KEYEVENTF_UNICODE` (each UTF-16 code unit separately, so surrogate pairs work). This was added specifically to avoid the "browser re-selects text on focus → `Ctrl+V` replaces the selection" failure mode.
   - **Image emoji** → snapshot the current clipboard, put `QImage` on the clipboard, synthesize `Ctrl+V`, wait 400 ms for the target app to consume it, restore the snapshot.

## Project layout

```
assets/emojis.json      bundled ~1850-entry emoji dataset (see scripts/build_emojis.py)
main.py                 wiring: tray + hotkeys + popup + settings + usage store
src/
  config.py             JSON config at %APPDATA%\SmartEmoji\config.json
  custom_store.py       user shortcodes + user images at %APPDATA%\SmartEmoji\custom.json + images/
  emoji_data.py         EmojiIndex: load bundled JSON, merge customs, search scoring
  foreground.py         Win32 GetGUIThreadInfo / GetCursorPos / SetForegroundWindow
  hotkeys.py            RegisterHotKey + Windows message loop in a QThread
  paste.py              SendInput helpers: send_ctrl_v() and send_unicode_text()
  startup.py            HKCU\...\Run registry entry for "launch at login"
  usage_store.py        per-emoji time-decayed score (14-day half-life) → "most used first"
  ui/
    popup.py            the picker: QLineEdit + QListWidget(IconMode) + custom QStyledItemDelegate
    settings.py         tabbed QDialog: Hotkeys / Shortcodes / Images / General
    theme.py            dark QSS
    tray.py             QSystemTrayIcon + menu
scripts/build_emojis.py one-off dataset builder (fetches emojilib, writes assets/emojis.json)
```

## Runtime data (never in the repo)

`%APPDATA%\SmartEmoji\`
- `config.json` — hotkeys, grid size, caption toggle
- `custom.json` — `{aliases: {code -> emoji_char}, images: [{id,name,codes,path}]}`
- `images/` — user-added image emojis (files copied in on add)
- `usage.json` — per-emoji `{count, last_used_timestamp}`

## Gotchas / things to know before editing

- **Search-box focus is intentional.** The popup's event filter on `self.search` intercepts arrow/Tab/Enter/Esc and forwards to the grid. Don't move focus to the grid — typing would stop filtering.
- **Hotkey thread must live in its own QThread.** `RegisterHotKey` only fires messages on the thread that registered it. `HotkeyManager.replace()` stops and restarts the thread when the user edits hotkeys in Settings.
- **Emoji grid uses a custom delegate (`EmojiDelegate`).** `QListWidget` in `IconMode` was eliding emoji characters to "..." at small cell sizes; the delegate paints the glyph directly via `QPainter.drawText` with `Qt.AlignCenter`.
- **Popup sizing is locked via `setFixedSize` in `apply_layout()`.** Earlier code relied on `adjustSize()` after a `setFixedWidth`, which refused to shrink the window once shown.
- **Window hide on deactivation** is done in `changeEvent` on `QEvent.ActivationChange`, not `focusOutEvent` — focus sits on the search box, so the popup widget itself never loses keyboard focus.
- **PyInstaller `--onefile` puts assets at `sys._MEIPASS`.** `emoji_data._bundled_path()` checks that before falling back to the source tree. If you add more bundled assets, remember to thread them through the same helper and add them to `-add-data` in the build command.
- **`startup._launcher_command()` is frozen-aware.** When running from the exe, it registers the exe path directly; when running from source, it finds a pythonw.exe in the local `.venv` or falls back to `sys.executable`.

## Build the portable EXE

```
pyinstaller --onefile --windowed --noconfirm --name SmartEmoji ^
    --add-data "assets/emojis.json;assets" main.py
```

Output: `dist/SmartEmoji.exe` — self-contained single file, no install needed. First run writes `%APPDATA%\SmartEmoji\config.json` with the default Ctrl+; hotkey.

## Rebuild the emoji dataset

```
python scripts/build_emojis.py
```

Fetches the latest `emoji-en-US.json` from `muan/emojilib`, re-ranks with a hand-curated popularity list, writes `assets/emojis.json`. Commit the output — the app must not depend on network at runtime.
