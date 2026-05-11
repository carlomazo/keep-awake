# Keep Awake

A lightweight Windows system tray app that prevents your PC from sleeping or locking — with smart pause features so it stays out of your way when you don't need it.

---

## Installation

Download the latest installer from the [Releases](https://github.com/carlomazo/keep-awake/releases/latest) page and run `keep_awake_setup.exe`.

The installer will:
- Install the app to Program Files
- Create a Start Menu shortcut
- Optionally add a desktop shortcut
- Optionally set the app to start with Windows

> **Note:** Windows SmartScreen may show a warning on first run. The installer is signed as **Keep Awake — carlomazo** (self-signed certificate). Click "More info" → "Run anyway" to proceed.

---

## Auto-update

The app checks for new releases automatically 30 seconds after startup. If a newer version is available, a notification appears in the tray. Click "Yes" to download and install the update silently.

---

## Features

### Core
- Prevents Windows sleep and screen-off via `SetThreadExecutionState`
- Optional mouse nudge (1px back-and-forth, returns to original position)
- Optional configurable key press (default: Scroll Lock)
- Green tray icon = active, red = paused
- Double-click tray icon to toggle

### Smart Pause
- **Meeting detection** — pauses automatically when MS Teams or Zoom is running
- **Battery guard** — pauses below a configurable battery threshold (default 20%), resumes on charger
- **Screen lock** — pauses when the screen locks, resumes when unlocked
- **Smart idle** — skips mouse nudge while you're actively typing or moving the mouse

### Schedule
- Up to 3 time blocks per day (e.g. 08:00–12:00 and 13:00–18:00)
- Per-day selection (Mon–Sun independently)
- Auto start/stop — app activates and pauses itself on schedule

### Profiles
- Save named configurations (interval, auto-stop, schedule)
- Switch profiles from the tray menu without opening Settings
- Double-click a profile to activate it directly

### Settings
- **General tab** — interval, auto-stop timer, keep-awake methods
- **Schedule tab** — time blocks and day selection
- **Profiles tab** — create, rename, reorder, activate profiles
- **System tab** — language (EN/PT-BR), theme (Dark/Light), hotkey, autostart, export/import config
- Changes apply immediately via Apply button (no restart needed)

### Log
- Usage log stored in `usage_log.csv` — every session recorded with date, start, end, duration
- Log viewer in Settings with List, Week, Month, and Chart views
- Export to standalone HTML report

### Other
- Configurable global hotkey (default `Ctrl+Shift+K`) to toggle from anywhere
- Start with Windows (registry autostart)
- Start paused option
- Single instance protection via Windows named mutex
- Balloon tip notifications on state changes

---

## Keyboard Shortcut

Default: `Ctrl+Shift+K` — toggles keep-awake from any window.

Reassignable in **Settings > System > Hotkey**.

---

## Project Structure

```
keep_awake.py       — entry point: tray menu, start/stop, hotkey, orchestration
state.py            — AppState dataclass, settings load/save, shared singleton
core.py             — translations, tooltip, icon, ctypes helpers, schedule logic
monitors.py         — background loops: keep-awake, tooltip, schedule, meeting, battery, lock
settings_ui.py      — full Settings window (Tkinter)
updater.py          — auto-update: checks GitHub API, downloads and runs installer
keep_awake_setup.iss — Inno Setup installer script
tests/
  test_core.py      — 51 unit tests for core logic
```

---

## Building from source

Requirements: Python 3.8+, `pystray`, `pyinstaller`, Inno Setup 6.

```bash
pip install pystray pyinstaller
python -m PyInstaller keep_awake.spec --noconfirm
# then compile keep_awake_setup.iss with Inno Setup
```

---

## Changelog

See [CHANGELOG.txt](CHANGELOG.txt) for full version history.
