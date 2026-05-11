# Keep Awake

A lightweight Windows system tray app that prevents your PC from sleeping or locking — with smart pause features so it stays out of your way when you don't need it.

---

## Installation

Download the latest installer from the [Releases](https://github.com/carlomazo/keep-awake/releases/latest) page and run `keep_awake_setup.exe`.

The installer will:
- Install the app to Program Files
- Create a Start Menu shortcut
- Optionally add a desktop shortcut
- Optionally register the app to start with Windows

> **Note:** Windows SmartScreen may show a warning on first run. The installer is signed as **Keep Awake — carlomazo** (self-signed certificate). Click "More info" → "Run anyway" to proceed.

---

## Features

### Core
- Prevents Windows sleep and screen-off via `SetThreadExecutionState`
- Optional mouse nudge — moves cursor 1px and back, returns to original position
- Optional configurable key press (default: Scroll Lock)
- Green tray icon = active, red = paused
- Double-click tray icon to toggle on/off

### Smart Pause
- **Meeting detection** — pauses automatically when MS Teams or Zoom is running; resumes when the meeting ends
- **Battery guard** — pauses when battery drops below a configurable threshold (default 20%); resumes when charger is connected
- **Screen lock** — pauses when the screen locks; resumes when unlocked
- **Smart idle** — skips mouse nudge while the user is actively typing or moving the mouse

### Schedule
- Up to 3 time blocks per day (e.g. 08:00–12:00 and 13:00–18:00)
- Per-day selection (Mon–Sun independently)
- Activates and pauses itself automatically based on the schedule

### Profiles
- Save named configurations (interval, auto-stop, schedule)
- Switch profiles from the tray menu without opening Settings
- Double-click a profile in the list to activate it directly

### Settings
- **General tab** — interval, auto-stop timer, keep-awake methods (API / mouse nudge / key press)
- **Schedule tab** — time blocks and day selection
- **Profiles tab** — create, rename, reorder, update, and activate profiles
- **System tab** — language (English / Português / Español), theme (Dark / Light), global hotkey, autostart, export/import config
- Apply changes without closing the window via the **Apply** button

### Log
- Every session recorded in `usage_log.csv` with date, start time, end time, and duration
- Log viewer inside Settings with **List**, **Week**, **Month**, and **Chart** views
- Export to a standalone HTML report
- Weekly summary notification — on first startup each week, shows last week's total time, active days, and daily average

### Other
- Global hotkey `Ctrl+Shift+K` — toggles keep-awake from any window (reassignable in Settings)
- Start with Windows via registry autostart
- Start paused option — app opens without activating keep-awake
- Single instance protection via Windows named mutex
- Balloon tip notifications on state changes

---

## Auto-Update

The app checks GitHub for new releases 30 seconds after startup. If a newer version is available, a notification appears in the tray. Clicking "Yes" downloads the new installer and runs it automatically.

---

## Keyboard Shortcut

Default: `Ctrl+Shift+K` — toggles keep-awake from any window.

Reassignable in **Settings > System > Global hotkey**.

---

## Project Structure

```
keep_awake.py        — entry point: tray menu, start/stop, hotkey, orchestration
state.py             — AppState dataclass, settings load/save, shared singleton
core.py              — translations (EN/PT/ES), tooltip, icon, ctypes helpers, schedule logic
monitors.py          — background loops: keep-awake, tooltip, schedule, meeting, battery, lock, weekly summary
settings_ui.py       — Settings window (Tkinter)
updater.py           — auto-update: checks GitHub releases API, downloads and runs installer
keep_awake_setup.iss — Inno Setup installer script
.github/
  workflows/
    release.yml      — GitHub Actions: builds exe + installer and attaches to release on tag push
  ISSUE_TEMPLATE/    — bug report and feature request templates
  pull_request_template.md
tests/
  test_core.py       — 51 unit tests covering core logic, schedule, tooltip, hotkey, versioning
```

---

## Building from Source

Requirements: Python 3.8+, `pystray`, `pyinstaller`, [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```bash
pip install pystray pyinstaller
python -m PyInstaller keep_awake.py --onefile --noconsole --name keep_awake --exclude-module PIL --exclude-module Pillow --noconfirm
# Compile keep_awake_setup.iss with Inno Setup to produce the installer
```

Releases are built automatically via GitHub Actions on every `v*` tag push — see `.github/workflows/release.yml`.

---

## Changelog

See [CHANGELOG.txt](CHANGELOG.txt) for full version history.
