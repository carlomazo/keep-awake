# -*- coding: utf-8 -*-
"""
keep_awake.py — Orchestrator: main(), start/stop, tray menu, hotkey.

This is the entry-point module.  All other modules import the shared
`state` singleton from state.py; they do NOT import keep_awake at the top
level (only inside functions to break the circular dependency).
"""

import ctypes
import ctypes.wintypes
import datetime
import os
import sys
import threading
import time
import winreg

import pystray
from pystray import MenuItem as item

from state import state, BASE_DIR, MUTEX_NAME, VERSION, save_settings, load_settings, _migrate_schedule_blocks
from core import (
    T,
    _build_tooltip,
    _format_duration,
    _format_hotkey,
    _in_schedule_window,
    _is_dark_mode,
    make_icon,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_ALT,
)
import monitors
from monitors import (
    notify,
    restore_idle_timer,
    _log_session,
    _start_schedule_thread,
    _start_meeting_monitor,
    _start_battery_monitor,
    _start_lock_monitor,
    tooltip_loop,
)
from settings_ui import open_settings

# ---------------------------------------------------------------------------
# Shutdown event — shared with monitors.py
# ---------------------------------------------------------------------------

_shutdown = threading.Event()
monitors._shutdown = _shutdown   # inject into monitors after import

# ---------------------------------------------------------------------------
# Autostart registry helpers
# ---------------------------------------------------------------------------

AUTOSTART_NAME = "KeepAwake"
AUTOSTART_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_autostart_path():
    # When frozen as .exe, register the exe itself; otherwise use start.bat
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.join(BASE_DIR, "start.bat")


def is_autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as k:
            winreg.QueryValueEx(k, AUTOSTART_NAME)
            return True
    except FileNotFoundError:
        return False


def enable_autostart():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, AUTOSTART_NAME, 0, winreg.REG_SZ, _get_autostart_path())


def disable_autostart():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, AUTOSTART_NAME)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Auto-stop timer
# ---------------------------------------------------------------------------

def _schedule_auto_stop(icon, seconds):
    if state.auto_stop_timer:
        state.auto_stop_timer.cancel()
    if seconds:
        state.auto_stop_timer = threading.Timer(seconds, lambda: stop_keeping(icon, None))
        state.auto_stop_timer.daemon = True
        state.auto_stop_timer.start()


# ---------------------------------------------------------------------------
# Start / Stop / Toggle / Quit
# ---------------------------------------------------------------------------

def start_keeping(icon, _item):
    if not state.running:
        state.running       = True
        state.active_since    = time.monotonic()
        state.active_since_dt = datetime.datetime.now()
        threading.Thread(target=monitors.keep_awake_loop, args=(icon,), daemon=True).start()
        icon.icon  = make_icon(True)
        icon.title = _build_tooltip()
        _schedule_auto_stop(icon, state.auto_stop_after)
        notify(icon, T("Keep Awake activated"))
        icon.update_menu()


def stop_keeping(icon, _item):
    if state.running:
        state.running = False
        if state.auto_stop_timer:
            state.auto_stop_timer.cancel()
            state.auto_stop_timer = None
        restore_idle_timer()
        _log_session(state.active_since_dt, datetime.datetime.now())
        icon.icon  = make_icon(False)
        icon.title = _build_tooltip()
        notify(icon, T("Keep Awake paused"))
        icon.update_menu()


def toggle_keeping(icon):
    if state.running:
        stop_keeping(icon, None)
    else:
        start_keeping(icon, None)


def quit_app(icon, _item):
    if state.running:
        _log_session(state.active_since_dt, datetime.datetime.now())
    state.running = False
    restore_idle_timer()
    save_settings()
    _unregister_hotkey()
    _shutdown.set()
    icon.stop()


# ---------------------------------------------------------------------------
# Interval / Auto-stop setters
# ---------------------------------------------------------------------------

def set_interval(seconds, icon):
    state.interval       = seconds
    state.active_profile = None
    save_settings()
    icon.update_menu()


def set_auto_stop(seconds, icon):
    state.auto_stop_after = seconds
    state.active_profile  = None
    if state.running:
        _schedule_auto_stop(icon, seconds)
        icon.title = _build_tooltip()
    save_settings()
    icon.update_menu()


def _prompt_custom_interval(icon):
    import tkinter as tk
    from tkinter import ttk

    def apply(event=None):
        val = entry.get().strip()
        if not val:
            set_interval(60, icon)
            root.destroy()
            return
        try:
            secs = int(val)
            if secs < 10:
                return
            set_interval(secs, icon)
            root.destroy()
        except ValueError:
            pass

    root = tk.Tk()
    root.title(T("Custom Interval"))
    root.resizable(False, False)
    root.attributes("-topmost", True)
    dark = _is_dark_mode()
    root.configure(bg="#1e1e1e" if dark else "#f0f0f0")
    style = ttk.Style(root); style.theme_use("clam")
    if dark:
        style.configure(".", background="#1e1e1e", foreground="#ffffff", fieldbackground="#2d2d2d")
        style.configure("TEntry", fieldbackground="#2d2d2d", foreground="#ffffff")
        style.configure("TButton", background="#3c3c3c", foreground="#ffffff")

    ttk.Label(root, text=T("Interval (e.g. 30, 90, 120 — seconds):")).pack(padx=16, pady=(14, 4))
    entry = ttk.Entry(root, width=12)
    entry.insert(0, str(state.interval))
    entry.pack(padx=16, pady=(0, 8))
    entry.select_range(0, tk.END)
    entry.focus()
    entry.bind("<Return>", apply)
    entry.bind("<Escape>", lambda e: root.destroy())
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    ttk.Button(root, text="OK", command=apply).pack(pady=(0, 12))
    root.mainloop()


def _prompt_custom_autostop(icon):
    import tkinter as tk
    from tkinter import ttk
    from core import _parse_duration

    def apply(event=None):
        val = entry.get().strip()
        if not val:
            set_auto_stop(None, icon)
            root.destroy()
            return
        secs, err = _parse_duration(val)
        if err or secs is None or secs < 10:
            return
        set_auto_stop(secs, icon)
        root.destroy()

    root = tk.Tk()
    root.title(T("Custom Auto-stop"))
    root.resizable(False, False)
    root.attributes("-topmost", True)
    dark = _is_dark_mode()
    root.configure(bg="#1e1e1e" if dark else "#f0f0f0")
    style = ttk.Style(root); style.theme_use("clam")
    if dark:
        style.configure(".", background="#1e1e1e", foreground="#ffffff", fieldbackground="#2d2d2d")
        style.configure("TEntry", fieldbackground="#2d2d2d", foreground="#ffffff")
        style.configure("TButton", background="#3c3c3c", foreground="#ffffff")

    ttk.Label(root, text=T("Auto-stop (e.g. 1h30m, 20m, 45s — blank = no limit):")).pack(padx=16, pady=(14, 4))
    entry = ttk.Entry(root, width=16)
    if state.auto_stop_after:
        entry.insert(0, _format_duration(state.auto_stop_after))
    entry.pack(padx=16, pady=(0, 8))
    entry.select_range(0, tk.END)
    entry.focus()
    entry.bind("<Return>", apply)
    entry.bind("<Escape>", lambda e: root.destroy())
    ttk.Button(root, text="OK", command=apply).pack(pady=(0, 12))
    root.mainloop()


# ---------------------------------------------------------------------------
# Profile management
# ---------------------------------------------------------------------------

def apply_profile(name, icon):
    if name not in state.profiles:
        return
    p = state.profiles[name]
    state.interval        = p["interval"]
    state.auto_stop_after = p["auto_stop_after"]
    if "schedule_blocks" in p:
        state.schedule_blocks = p["schedule_blocks"]
    else:
        state.schedule_blocks = _migrate_schedule_blocks(p)
    state.schedule_days  = set(p.get("schedule_days", sorted(state.schedule_days)))
    state.active_profile = name
    if state.running:
        _schedule_auto_stop(icon, state.auto_stop_after)
        icon.title = _build_tooltip()
    save_settings()
    notify(icon, T("Profile activated").format(name=name))
    icon.update_menu()


# ---------------------------------------------------------------------------
# Tray menu
# ---------------------------------------------------------------------------

def build_menu(icon_ref):
    def interval_item(label, secs):
        return item(label,
                    lambda ic, it: set_interval(secs, ic),
                    checked=lambda _: state.interval == secs,
                    radio=True)

    def auto_stop_item(label, secs):
        return item(label,
                    lambda ic, it: set_auto_stop(secs, ic),
                    checked=lambda _: state.auto_stop_after == secs,
                    radio=True)

    def profile_items():
        if not state.profiles:
            return (item(T("No profiles saved"), lambda ic, it: None, enabled=lambda _: False),)
        result = []
        for name in state.profiles:
            def _make_action(n):
                def _action(ic, it): apply_profile(n, ic)
                return _action
            def _make_checked(n):
                return lambda _: state.active_profile == n
            result.append(item(name, _make_action(name), checked=_make_checked(name)))
        return tuple(result)

    return (
        item("Toggle", lambda ic, it: toggle_keeping(ic), default=True, visible=False),
        item(lambda _: T("Start"), start_keeping, enabled=lambda _: not state.running),
        item(lambda _: T("Stop"),  stop_keeping,  enabled=lambda _: state.running),
        pystray.Menu.SEPARATOR,
        item(lambda _: T("Interval"), pystray.Menu(
            interval_item(T("30 seconds"), 30),
            interval_item(T("1 minute"),   60),
            interval_item(T("2 minutes"),  120),
            item(lambda _: f"{T('Custom')} ({_format_duration(state.interval)})" if state.interval not in (30, 60, 120) else T("Custom"),
                 lambda ic, it: threading.Thread(target=_prompt_custom_interval, args=(ic,), daemon=True).start(),
                 checked=lambda _: state.interval not in (30, 60, 120),
                 radio=True),
        )),
        item(lambda _: T("Auto-stop"), pystray.Menu(
            auto_stop_item(T("No limit"),  None),
            auto_stop_item(T("1 hour"),    3600),
            auto_stop_item(T("2 hours"),   7200),
            auto_stop_item(T("4 hours"),   14400),
            item(lambda _: f"{T('Custom')} ({_format_duration(state.auto_stop_after)})" if state.auto_stop_after and state.auto_stop_after not in (3600, 7200, 14400) else T("Custom"),
                 lambda ic, it: threading.Thread(target=_prompt_custom_autostop, args=(ic,), daemon=True).start(),
                 checked=lambda _: state.auto_stop_after is not None and state.auto_stop_after not in (3600, 7200, 14400),
                 radio=True),
        )),
        item(lambda _: f"{T('Profiles')} ({state.active_profile})" if state.active_profile else T("Profiles"),
             pystray.Menu(lambda: profile_items())),
        pystray.Menu.SEPARATOR,
        item(lambda _: T("Settings"), lambda ic, it: threading.Thread(
            target=open_settings, args=(ic,), daemon=True).start()),
        pystray.Menu.SEPARATOR,
        item(lambda _: T("Changelog"), lambda ic, it: os.startfile(os.path.join(BASE_DIR, "CHANGELOG.txt"))),
        item(lambda _: T("Quit"), quit_app),
    )


# ---------------------------------------------------------------------------
# Global hotkey (Ctrl+Shift+K) via Win32 RegisterHotKey
# ---------------------------------------------------------------------------

HOTKEY_ID = 1

_hotkey_thread = None


def _hotkey_listener(icon):
    ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, state.hotkey_mods, state.hotkey_vk)
    msg = ctypes.wintypes.MSG()
    while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == 0x0312 and msg.wParam == HOTKEY_ID:  # WM_HOTKEY
            toggle_keeping(icon)
    ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)


def _register_hotkey(icon):
    global _hotkey_thread
    _hotkey_thread = threading.Thread(target=_hotkey_listener, args=(icon,), daemon=True)
    _hotkey_thread.start()


def _unregister_hotkey():
    global _hotkey_thread
    if _hotkey_thread and _hotkey_thread.ident:
        ctypes.windll.user32.PostThreadMessageW(
            _hotkey_thread.ident, 0x0012, 0, 0)  # WM_QUIT
    _hotkey_thread = None


def _reregister_hotkey(icon):
    _unregister_hotkey()
    time.sleep(0.15)
    _register_hotkey(icon)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import traceback
    log_path = os.path.join(BASE_DIR, "startup.log")

    def _log(msg):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now().isoformat()} {msg}\n")
        except Exception:
            pass

    _log("main() started")

    # Prevent multiple instances via Windows named mutex
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        _log("already running — showing message box")
        ctypes.windll.user32.MessageBoxW(
            0,
            T("Keep Awake is already running.\nCheck the system tray."),
            "Keep Awake",
            0x40 | 0x1000,  # MB_ICONINFORMATION | MB_SYSTEMMODAL
        )
        return

    _log("mutex acquired")

    try:
        load_settings()
        _log("settings loaded")

        icon = pystray.Icon("keep_awake", make_icon(False), "Keep Awake — paused")
        icon.menu = pystray.Menu(*build_menu(icon))
        _log("icon object created")

        def setup(ic):
            _log("setup() called — making icon visible")
            try:
                ic.visible = True
                _log("icon visible")
                threading.Thread(target=tooltip_loop, args=(ic,), daemon=True).start()
                _register_hotkey(ic)
                if state.meeting_detection:
                    _start_meeting_monitor(ic)
                if state.battery_guard:
                    _start_battery_monitor(ic)
                if state.lock_guard:
                    _start_lock_monitor(ic)
                if state.schedule_enabled:
                    _start_schedule_thread(ic)
                    if _in_schedule_window():
                        start_keeping(ic, None)
                elif not state.start_paused:
                    start_keeping(ic, None)
                from updater import start_update_checker
                start_update_checker(notify_fn=lambda msg: notify(ic, msg))
                _log("setup() complete")
            except Exception:
                _log("ERROR in setup():\n" + traceback.format_exc())

        _log("calling icon.run()")
        icon.run(setup=setup)
        _log("icon.run() returned")
    except Exception:
        _log("FATAL ERROR:\n" + traceback.format_exc())

    ctypes.windll.kernel32.ReleaseMutex(mutex)
    ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
