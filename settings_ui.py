# -*- coding: utf-8 -*-
"""
settings_ui.py — Settings dialog (Tkinter).

Imports everything from state, core, monitors, and keep_awake.
"""

import json
import os
import threading

from state import state, BASE_DIR, SETTINGS_FILE, LOG_FILE, save_settings, _migrate_schedule_blocks
from core import (
    T,
    _parse_duration,
    _format_duration,
    _build_tooltip,
    _is_dark_mode,
    _format_hotkey,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_ALT,
)
from monitors import (
    notify,
    _start_schedule_thread,
    _start_meeting_monitor,
    _start_battery_monitor,
    _start_lock_monitor,
)


def open_settings(icon):
    try:
        _open_settings_inner(icon)
    except Exception:
        import traceback
        with open(os.path.join(BASE_DIR, "settings_error.log"), "w", encoding="utf-8") as _f:
            traceback.print_exc(file=_f)


def _open_settings_inner(icon):
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
    import csv as _csv

    # Defer the circular imports (keep_awake imports us back).
    import keep_awake as _ka

    def _apply_theme(style):
        dark     = _is_dark_mode()
        BG       = "#1e1e1e" if dark else "#f0f0f0"
        FG       = "#ffffff" if dark else "#000000"
        ENTRY_BG = "#2d2d2d" if dark else "#ffffff"
        BTN_BG   = "#3c3c3c" if dark else "#e0e0e0"
        BTN_ACT  = "#555555" if dark else "#cccccc"
        root.configure(bg=BG)
        style.configure(".",                 background=BG,       foreground=FG, fieldbackground=ENTRY_BG)
        style.configure("TLabel",            background=BG,       foreground=FG)
        style.configure("TFrame",            background=BG)
        style.configure("TLabelframe",       background=BG,       foreground=FG)
        style.configure("TLabelframe.Label", background=BG,       foreground=FG)
        style.configure("TEntry",            fieldbackground=ENTRY_BG, foreground=FG)
        style.configure("TButton",           background=BTN_BG,   foreground=FG)
        style.configure("TNotebook",         background=BG)
        style.configure("TNotebook.Tab",     background=BTN_BG,   foreground=FG)
        style.map("TButton", background=[("active", BTN_ACT)])

    dark = _is_dark_mode()
    BG   = "#1e1e1e" if dark else "#f0f0f0"
    FG   = "#ffffff" if dark else "#000000"
    ENTRY_BG = "#2d2d2d" if dark else "#ffffff"
    BTN_BG   = "#3c3c3c" if dark else "#e0e0e0"

    root = tk.Tk()
    root.title(T("Keep Awake — Settings"))
    root.resizable(True, True)
    root.minsize(420, 400)
    root.attributes("-topmost", True)
    root.configure(bg=BG)

    style = ttk.Style(root)
    style.theme_use("clam")
    _apply_theme(style)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    nb = ttk.Notebook(root)
    nb.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 4))

    # ── Tab: General ──────────────────────────────────────────────
    tab_general = ttk.Frame(nb)
    nb.add(tab_general, text=T(" General "))
    tab_general.columnconfigure(0, weight=1)

    ttk.Label(tab_general, text=T("Interval in seconds (blank = use quick menu selection)")).grid(
        row=0, column=0, sticky="w", padx=10, pady=(10, 2))
    entry_interval = ttk.Entry(tab_general, width=14)
    entry_interval.insert(0, str(state.interval))
    entry_interval.grid(row=1, column=0, padx=10, pady=(0, 8), sticky="w")

    ttk.Label(tab_general, text=T("Auto-stop (e.g. 1h30m, 20m, 45s — blank = no limit)")).grid(
        row=2, column=0, sticky="w", padx=10, pady=(4, 2))
    entry_autostop = ttk.Entry(tab_general, width=14)
    if state.auto_stop_after:
        entry_autostop.insert(0, _format_duration(state.auto_stop_after))
    entry_autostop.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="w")

    # Keep-awake methods
    ttk.Label(tab_general, text=T("Keep-awake methods")).grid(
        row=4, column=0, sticky="w", padx=10, pady=(8, 2))
    keep_api_var   = tk.BooleanVar(value=state.keep_api)
    keep_mouse_var = tk.BooleanVar(value=state.keep_mouse)
    keep_key_var   = tk.BooleanVar(value=state.keep_key)
    ttk.Checkbutton(tab_general, text=T("System API (prevent sleep / screen off)"),
                    variable=keep_api_var).grid(row=5, column=0, sticky="w", padx=24, pady=2)
    ttk.Checkbutton(tab_general, text=T("Mouse nudge (move cursor 1px)"),
                    variable=keep_mouse_var).grid(row=6, column=0, sticky="w", padx=24, pady=2)

    key_frame = ttk.Frame(tab_general)
    key_frame.grid(row=7, column=0, sticky="w", padx=24, pady=2)
    ttk.Checkbutton(key_frame, text=T("Key press"), variable=keep_key_var).pack(side="left")

    def _vk_to_label(vk):
        _names = {0x91: "Scroll Lock", 0x13: "Pause", 0x14: "Caps Lock",
                  0x90: "Num Lock", 0x7A: "F11", 0x7B: "F12",
                  0x77: "F8", 0x78: "F9", 0x79: "F10"}
        if vk in _names:
            return _names[vk]
        if 0x41 <= vk <= 0x5A:
            return chr(vk)
        return f"0x{vk:02X}"

    _pending_nudge_key = [state.nudge_key_vk]
    nudge_key_label = tk.StringVar(value=f"({_vk_to_label(state.nudge_key_vk)})")
    nudge_key_btn = ttk.Button(key_frame, textvariable=nudge_key_label, width=14)
    nudge_key_btn.pack(side="left", padx=(6, 0))

    nudge_key_hint = tk.StringVar()
    ttk.Label(key_frame, textvariable=nudge_key_hint, foreground="#888888").pack(side="left", padx=(6, 0))

    _capturing_nudge = [False]

    def _start_nudge_capture(event=None):
        if _capturing[0]:          # hotkey capture active — cancel it
            _capturing[0] = False
            root.unbind("<KeyPress>")
        if _capturing_nudge[0]:
            return
        _capturing_nudge[0] = True
        nudge_key_label.set(T("Click then press a key (nudge)"))
        nudge_key_hint.set("")
        nudge_key_btn.focus_set()
        root.bind("<KeyPress>", _on_nudge_key_capture)

    def _on_nudge_key_capture(event):
        _MODIFIERS = {"Control_L", "Control_R", "Shift_L", "Shift_R",
                      "Alt_L", "Alt_R", "Super_L", "Super_R"}
        if event.keysym in _MODIFIERS:
            return
        _VK_MAP = {
            "Scroll_Lock": 0x91, "Pause": 0x13, "Caps_Lock": 0x14,
            "Num_Lock": 0x90, "F8": 0x77, "F9": 0x78, "F10": 0x79,
            "F11": 0x7A, "F12": 0x7B,
        }
        sym = event.keysym
        if sym in _VK_MAP:
            vk = _VK_MAP[sym]
        elif len(sym) == 1 and sym.upper().isalpha():
            vk = ord(sym.upper())
        else:
            nudge_key_hint.set("Unsupported key")
            _capturing_nudge[0] = False
            root.unbind("<KeyPress>")
            return
        _pending_nudge_key[0] = vk
        nudge_key_label.set(f"({_vk_to_label(vk)})")
        nudge_key_hint.set("✓")
        _capturing_nudge[0] = False
        root.unbind("<KeyPress>")

    nudge_key_btn.bind("<Button-1>", _start_nudge_capture)

    # ── Tab: Schedule ─────────────────────────────────────────────
    tab_sched = ttk.Frame(nb)
    nb.add(tab_sched, text=T(" Schedule "))
    tab_sched.columnconfigure(0, weight=1)

    sched_enabled_var = tk.BooleanVar(value=state.schedule_enabled)
    ttk.Checkbutton(tab_sched, text=T("Enable schedule"),
                    variable=sched_enabled_var).grid(
        row=0, column=0, sticky="w", padx=10, pady=(12, 6))

    ttk.Label(tab_sched, text=T("Active days")).grid(
        row=1, column=0, sticky="w", padx=10, pady=(4, 4))

    day_names = [T("Mon"), T("Tue"), T("Wed"), T("Thu"), T("Fri"), T("Sat"), T("Sun")]
    day_vars = [tk.BooleanVar(value=(i in state.schedule_days)) for i in range(7)]
    days_frame = ttk.Frame(tab_sched)
    days_frame.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))
    for i, (name, var) in enumerate(zip(day_names, day_vars)):
        ttk.Checkbutton(days_frame, text=name, variable=var).grid(
            row=0, column=i, padx=(0, 6))

    ttk.Label(tab_sched, text=T("Time blocks (up to 3)")).grid(
        row=3, column=0, sticky="w", padx=10, pady=(4, 4))

    # Pad schedule_blocks to 3 entries for the UI
    _pad_blocks = (state.schedule_blocks + [{}, {}, {}])[:3]

    block_entries = []  # list of (sh, sm, eh, em) entry widgets
    blocks_frame = ttk.Frame(tab_sched)
    blocks_frame.grid(row=4, column=0, sticky="w", padx=10, pady=(0, 4))

    for bi in range(3):
        b = _pad_blocks[bi]
        sh_val = f"{b['start'][0]:02d}" if b.get("start") else ""
        sm_val = f"{b['start'][1]:02d}" if b.get("start") else ""
        eh_val = f"{b['end'][0]:02d}"   if b.get("end")   else ""
        em_val = f"{b['end'][1]:02d}"   if b.get("end")   else ""

        ttk.Label(blocks_frame, text=f"{bi+1}.").grid(row=bi, column=0, padx=(0, 4), pady=3)
        ttk.Label(blocks_frame, text=T("Start_label")).grid(row=bi, column=1, padx=(0, 2))
        e_sh = ttk.Entry(blocks_frame, width=4); e_sh.insert(0, sh_val)
        e_sh.grid(row=bi, column=2)
        ttk.Label(blocks_frame, text=":").grid(row=bi, column=3, padx=1)
        e_sm = ttk.Entry(blocks_frame, width=4); e_sm.insert(0, sm_val)
        e_sm.grid(row=bi, column=4)
        ttk.Label(blocks_frame, text=f"  {T('End_label')}").grid(row=bi, column=5, padx=(4, 2))
        e_eh = ttk.Entry(blocks_frame, width=4); e_eh.insert(0, eh_val)
        e_eh.grid(row=bi, column=6)
        ttk.Label(blocks_frame, text=":").grid(row=bi, column=7, padx=1)
        e_em = ttk.Entry(blocks_frame, width=4); e_em.insert(0, em_val)
        e_em.grid(row=bi, column=8)
        block_entries.append((e_sh, e_sm, e_eh, e_em))

    ttk.Label(tab_sched, text=T("Leave Start/End blank to skip a block."),
              foreground="#888888").grid(row=5, column=0, sticky="w", padx=10, pady=(2, 10))

    # ── Tab: Profiles ─────────────────────────────────────────────
    tab_profiles = ttk.Frame(nb)
    nb.add(tab_profiles, text=T(" Profiles "))
    tab_profiles.columnconfigure(0, weight=1)

    prof_listbox = tk.Listbox(tab_profiles, listvariable=tk.StringVar(value=list(state.profiles.keys())),
                               width=22, height=6,
                               bg=ENTRY_BG, fg=FG, selectbackground="#0078d4",
                               relief="flat", bd=1)
    prof_listbox.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 4), sticky="ew")

    def _refresh_listbox():
        prof_listbox.delete(0, tk.END)
        for name in state.profiles:
            label = f"{'★ ' if name == state.active_profile else ''}{name}"
            prof_listbox.insert(tk.END, label)

    _refresh_listbox()

    def _add_profile():
        name = simpledialog.askstring(T("New profile"), T("Profile name:"), parent=root)
        if not name or not name.strip():
            return
        name = name.strip()
        cur_blocks = []
        for e_sh, e_sm, e_eh, e_em in block_entries:
            sh_v = e_sh.get().strip(); sm_v = e_sm.get().strip()
            eh_v = e_eh.get().strip(); em_v = e_em.get().strip()
            if not any([sh_v, sm_v, eh_v, em_v]):
                continue
            try:
                cur_blocks.append({"start": [int(sh_v), int(sm_v)], "end": [int(eh_v), int(em_v)]})
            except ValueError:
                pass
        if not cur_blocks:
            cur_blocks = list(state.schedule_blocks)
        val_interval = entry_interval.get().strip()
        cur_interval = int(val_interval) if val_interval else state.interval
        val_stop = entry_autostop.get().strip()
        cur_autostop, _ = _parse_duration(val_stop) if val_stop else (state.auto_stop_after, None)
        cur_days = sorted(i for i, v in enumerate(day_vars) if v.get()) or sorted(state.schedule_days)
        state.profiles[name] = {
            "interval":        cur_interval,
            "auto_stop_after": cur_autostop,
            "schedule_blocks": cur_blocks,
            "schedule_days":   cur_days,
        }
        state.active_profile = name
        _refresh_listbox()

    def _delete_profile():
        sel = prof_listbox.curselection()
        if not sel:
            return
        raw = prof_listbox.get(sel[0]).lstrip("★ ")
        if raw in state.profiles:
            del state.profiles[raw]
        if state.active_profile == raw:
            state.active_profile = None
        _refresh_listbox()
        icon.update_menu()

    def _activate_profile():
        sel = prof_listbox.curselection()
        if not sel:
            return
        raw = prof_listbox.get(sel[0]).lstrip("★ ")
        if raw not in state.profiles:
            return
        p = state.profiles[raw]
        state.interval        = p["interval"]
        state.auto_stop_after = p["auto_stop_after"]
        # support old profiles with schedule_start/end
        state.schedule_blocks = _migrate_schedule_blocks(p)
        state.schedule_days   = set(p.get("schedule_days", sorted(state.schedule_days)))
        state.active_profile  = raw
        entry_interval.delete(0, tk.END)
        entry_interval.insert(0, str(state.interval))
        entry_autostop.delete(0, tk.END)
        if state.auto_stop_after:
            entry_autostop.insert(0, _format_duration(state.auto_stop_after))
        _pad = (state.schedule_blocks + [{}, {}, {}])[:3]
        for bi, (e_sh, e_sm, e_eh, e_em) in enumerate(block_entries):
            b = _pad[bi]
            for e in (e_sh, e_sm, e_eh, e_em):
                e.delete(0, tk.END)
            if "start" in b and b["start"]:
                e_sh.insert(0, f"{b['start'][0]:02d}"); e_sm.insert(0, f"{b['start'][1]:02d}")
                e_eh.insert(0, f"{b['end'][0]:02d}");   e_em.insert(0, f"{b['end'][1]:02d}")
        for i, v in enumerate(day_vars):
            v.set(i in state.schedule_days)
        _refresh_listbox()
        icon.update_menu()
        _show_details()

    def _show_details(event=None):
        sel = prof_listbox.curselection()
        if not sel:
            detail_var.set(T("Select a profile to see its settings."))
            return
        raw = prof_listbox.get(sel[0]).lstrip("★ ")
        p = state.profiles.get(raw)
        if not p:
            detail_var.set("")
            return
        iv   = _format_duration(p["interval"])
        asv  = _format_duration(p["auto_stop_after"]) if p["auto_stop_after"] else "No limit"
        sd   = p.get("schedule_days")
        days_str = "".join(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"][i] for i in sorted(sd)) if sd is not None else "Mo–Fr"
        if "schedule_blocks" in p:
            blks = ", ".join(f"{b['start'][0]:02d}:{b['start'][1]:02d}–{b['end'][0]:02d}:{b['end'][1]:02d}" for b in p["schedule_blocks"])
            sched = f"{days_str} {blks}"
        elif "schedule_start" in p:
            ss = p["schedule_start"]; se = p["schedule_end"]
            sched = f"{days_str} {ss[0]:02d}:{ss[1]:02d}–{se[0]:02d}:{se[1]:02d}"
        else:
            sched = "not saved"
        detail_var.set(f"Interval: {iv}     Auto-stop: {asv}     Schedule: {sched}")

    def _edit_profile():
        sel = prof_listbox.curselection()
        if not sel:
            return
        raw = prof_listbox.get(sel[0]).lstrip("★ ")
        if raw not in state.profiles:
            return
        new_name = simpledialog.askstring(T("Rename profile"), T("New name:"), initialvalue=raw, parent=root)
        if not new_name or not new_name.strip() or new_name.strip() == raw:
            return
        new_name = new_name.strip()
        state.profiles[new_name] = state.profiles.pop(raw)
        if state.active_profile == raw:
            state.active_profile = new_name
        _refresh_listbox()
        icon.update_menu()

    def _update_profile():
        sel = prof_listbox.curselection()
        if not sel:
            return
        raw = prof_listbox.get(sel[0]).lstrip("★ ")
        if raw not in state.profiles:
            return
        val_interval = entry_interval.get().strip()
        cur_interval = int(val_interval) if val_interval else state.interval
        val_stop = entry_autostop.get().strip()
        cur_autostop, _ = _parse_duration(val_stop) if val_stop else (state.auto_stop_after, None)
        cur_blocks = []
        for e_sh, e_sm, e_eh, e_em in block_entries:
            sh_v = e_sh.get().strip(); sm_v = e_sm.get().strip()
            eh_v = e_eh.get().strip(); em_v = e_em.get().strip()
            if not any([sh_v, sm_v, eh_v, em_v]):
                continue
            try:
                cur_blocks.append({"start": [int(sh_v), int(sm_v)], "end": [int(eh_v), int(em_v)]})
            except ValueError:
                pass
        if not cur_blocks:
            cur_blocks = list(state.schedule_blocks)
        cur_days = sorted(i for i, v in enumerate(day_vars) if v.get()) or sorted(state.schedule_days)
        state.profiles[raw] = {
            "interval":        cur_interval,
            "auto_stop_after": cur_autostop,
            "schedule_blocks": cur_blocks,
            "schedule_days":   cur_days,
        }
        _refresh_listbox()
        _show_details()

    btn_frame = ttk.Frame(tab_profiles)
    btn_frame.grid(row=1, column=0, columnspan=2, pady=4)
    ttk.Button(btn_frame, text=T("Add current"), command=_add_profile).pack(side="left", padx=4)
    ttk.Button(btn_frame, text=T("Activate"),    command=_activate_profile).pack(side="left", padx=4)
    ttk.Button(btn_frame, text=T("Edit"),        command=_edit_profile).pack(side="left", padx=4)
    ttk.Button(btn_frame, text=T("Update"),      command=_update_profile).pack(side="left", padx=4)
    ttk.Button(btn_frame, text=T("Delete"),      command=_delete_profile).pack(side="left", padx=4)

    detail_var = tk.StringVar(value=T("Select a profile to see its settings."))
    ttk.Label(tab_profiles, textvariable=detail_var, foreground="#0078d4").grid(
        row=2, column=0, columnspan=2, padx=10, pady=(4, 2), sticky="w")

    ttk.Label(tab_profiles,
              text=T("'Add current' saves interval + auto-stop as a new profile."),
              foreground="#888888").grid(row=3, column=0, columnspan=2, padx=10, pady=(2, 10))

    prof_listbox.bind("<<ListboxSelect>>", _show_details)
    prof_listbox.bind("<Double-Button-1>", lambda e: _activate_profile())

    # Drag to reorder
    _drag_start = [None]

    def _drag_begin(event):
        _drag_start[0] = prof_listbox.nearest(event.y)

    def _drag_end(event):
        src = _drag_start[0]
        if src is None:
            return
        dst = prof_listbox.nearest(event.y)
        if dst == src:
            return
        keys = list(state.profiles.keys())
        keys.insert(dst, keys.pop(src))
        reordered = {k: state.profiles[k] for k in keys}
        state.profiles.clear()
        state.profiles.update(reordered)
        _refresh_listbox()
        prof_listbox.selection_set(dst)
        _show_details()
        icon.update_menu()

    prof_listbox.bind("<ButtonPress-1>",   _drag_begin)
    prof_listbox.bind("<ButtonRelease-1>", _drag_end)

    # ── Tab: System ───────────────────────────────────────────────
    tab_system = ttk.Frame(nb)
    nb.add(tab_system, text=T(" System "))
    tab_system.columnconfigure(0, weight=1)

    # Start with Windows
    autostart_var = tk.BooleanVar(value=_ka.is_autostart_enabled())
    ttk.Checkbutton(tab_system, text=T("Start with Windows"),
                    variable=autostart_var).grid(
        row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(14, 4))

    # Meeting detection
    meeting_var = tk.BooleanVar(value=state.meeting_detection)
    ttk.Checkbutton(tab_system, text=T("Pause during Teams / Zoom meetings"),
                    variable=meeting_var).grid(
        row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))

    # Smart pause
    smart_pause_var = tk.BooleanVar(value=state.smart_pause)
    smart_pause_frame = ttk.Frame(tab_system)
    smart_pause_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))
    ttk.Checkbutton(smart_pause_frame, text=T("Skip mouse nudge when user is active for less than"),
                    variable=smart_pause_var).pack(side="left")
    smart_pause_secs_var = tk.StringVar(value=str(state.smart_pause_secs))
    ttk.Entry(smart_pause_frame, textvariable=smart_pause_secs_var, width=4).pack(side="left", padx=4)
    ttk.Label(smart_pause_frame, text=T("seconds idle")).pack(side="left")

    # Battery guard
    battery_guard_var = tk.BooleanVar(value=state.battery_guard)
    battery_frame = ttk.Frame(tab_system)
    battery_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 6))
    ttk.Checkbutton(battery_frame, text=T("Pause when battery below"),
                    variable=battery_guard_var).pack(side="left")
    battery_threshold_var = tk.StringVar(value=str(state.battery_threshold))
    ttk.Entry(battery_frame, textvariable=battery_threshold_var, width=4).pack(side="left", padx=4)
    ttk.Label(battery_frame, text="%").pack(side="left")

    # Lock guard
    lock_guard_var = tk.BooleanVar(value=state.lock_guard)
    ttk.Checkbutton(tab_system, text=T("Pause when screen is locked"),
                    variable=lock_guard_var).grid(
        row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 4))

    # Start paused
    start_paused_var = tk.BooleanVar(value=state.start_paused)
    ttk.Checkbutton(tab_system, text=T("Start paused (do not activate on launch)"),
                    variable=start_paused_var).grid(
        row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 6))

    # Theme
    ttk.Label(tab_system, text=T("Theme")).grid(
        row=6, column=0, sticky="w", padx=10, pady=(8, 2))
    theme_var = tk.StringVar(value=state.theme)
    for i, (label, val) in enumerate([(T("Dark"), "dark"), (T("Light"), "light")]):
        ttk.Radiobutton(tab_system, text=label, variable=theme_var, value=val).grid(
            row=7 + i, column=0, sticky="w", padx=24, pady=2)

    # Language
    ttk.Label(tab_system, text=T("Language")).grid(
        row=9, column=0, sticky="w", padx=10, pady=(8, 2))
    language_var = tk.StringVar(value=state.language)
    for i, (label, val) in enumerate([("English", "en"), ("Português", "pt"), ("Español", "es")]):
        ttk.Radiobutton(tab_system, text=label, variable=language_var, value=val).grid(
            row=10 + i, column=0, sticky="w", padx=24, pady=2)

    ttk.Separator(tab_system, orient="horizontal").grid(
        row=13, column=0, columnspan=2, sticky="ew", padx=10, pady=(14, 6))

    def _reset_defaults():
        if not messagebox.askyesno(T("Reset to defaults_title"),
                                   T("Reset all settings to defaults?\nProfiles will be kept."),
                                   parent=root):
            return
        entry_interval.delete(0, tk.END)
        entry_autostop.delete(0, tk.END)
        for e_sh, e_sm, e_eh, e_em in block_entries:
            for e in (e_sh, e_sm, e_eh, e_em):
                e.delete(0, tk.END)
        block_entries[0][0].insert(0, "08"); block_entries[0][1].insert(0, "00")
        block_entries[0][2].insert(0, "18"); block_entries[0][3].insert(0, "00")
        sched_enabled_var.set(False)
        for i, v in enumerate(day_vars):
            v.set(i < 5)  # Mon–Fri
        theme_var.set("light")
        meeting_var.set(False)
        smart_pause_var.set(False)
        smart_pause_secs_var.set("30")
        battery_guard_var.set(False)
        battery_threshold_var.set("20")
        lock_guard_var.set(False)
        keep_api_var.set(True)
        keep_mouse_var.set(True)
        keep_key_var.set(False)
        _pending_nudge_key[0] = 0x91
        nudge_key_label.set("(Scroll Lock)")
        start_paused_var.set(False)

    ttk.Button(tab_system, text=T("Reset to defaults"), command=_reset_defaults).grid(
        row=14, column=0, sticky="w", padx=10, pady=(0, 6))

    ttk.Separator(tab_system, orient="horizontal").grid(
        row=15, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 6))

    # Global hotkey
    ttk.Label(tab_system, text=T("Global hotkey (toggle)")).grid(
        row=16, column=0, sticky="w", padx=10, pady=(4, 2))

    _pending_hotkey = [state.hotkey_mods, state.hotkey_vk]

    hotkey_var = tk.StringVar(value=_format_hotkey(state.hotkey_mods, state.hotkey_vk))
    hotkey_btn = ttk.Button(tab_system, textvariable=hotkey_var, width=20)
    hotkey_btn.grid(row=17, column=0, sticky="w", padx=24, pady=(0, 4))

    hotkey_hint = tk.StringVar(value=T("Click then press a key combo"))
    ttk.Label(tab_system, textvariable=hotkey_hint, foreground="#888888").grid(
        row=18, column=0, sticky="w", padx=24, pady=(0, 8))

    _capturing = [False]

    def _start_capture(event=None):
        if _capturing_nudge[0]:    # nudge capture active — cancel it
            _capturing_nudge[0] = False
            root.unbind("<KeyPress>")
        if _capturing[0]:
            return
        _capturing[0] = True
        hotkey_var.set(T("Press a key combo…"))
        hotkey_hint.set(T("Hold Ctrl/Shift/Alt, then press a letter"))
        hotkey_btn.focus_set()
        root.bind("<KeyPress>", _on_key_capture)

    def _on_key_capture(event):
        if event.keysym in ("Control_L", "Control_R", "Shift_L", "Shift_R",
                             "Alt_L", "Alt_R", "Super_L", "Super_R"):
            return
        mods = 0
        if event.state & 0x4:     mods |= MOD_CONTROL
        if event.state & 0x1:     mods |= MOD_SHIFT
        if event.state & 0x20000: mods |= MOD_ALT
        if not mods:
            hotkey_hint.set(T("Must include Ctrl, Shift, or Alt — try again"))
            return
        sym = event.keysym.upper()
        if len(sym) == 1 and sym.isalpha():
            vk = ord(sym)
        else:
            hotkey_hint.set(T("Only letters A–Z are supported — try again"))
            return
        _pending_hotkey[0] = mods
        _pending_hotkey[1] = vk
        hotkey_var.set(_format_hotkey(mods, vk))
        hotkey_hint.set(T("Hotkey captured — click Apply/Save to activate"))
        _capturing[0] = False
        root.unbind("<KeyPress>")

    hotkey_btn.bind("<Button-1>", _start_capture)

    ttk.Separator(tab_system, orient="horizontal").grid(
        row=19, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 6))

    def _export_settings():
        from tkinter import filedialog
        from state import _settings_to_dict
        path = filedialog.asksaveasfilename(
            parent=root, defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="keep_awake_settings.json",
            title="Export settings")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(_settings_to_dict(), f, indent=2)
            notify(icon, T("Settings exported"))
        except Exception as e:
            messagebox.showerror(T("Export failed"), str(e), parent=root)

    def _import_settings():
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=root, filetypes=[("JSON files", "*.json")], title="Import settings")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            state.interval        = d.get("interval", 60)
            state.auto_stop_after = d.get("auto_stop_after", None)
            state.schedule_blocks   = _migrate_schedule_blocks(d)
            state.schedule_days   = set(d.get("schedule_days", [0, 1, 2, 3, 4]))
            state.profiles        = d.get("profiles", {})
            state.active_profile  = d.get("active_profile", None)
            state.theme           = d.get("theme", "light")
            state.hotkey_mods     = d.get("hotkey_mods", 0x0002 | 0x0004)
            state.hotkey_vk       = d.get("hotkey_vk",   0x4B)
            # Refresh all form fields
            entry_interval.delete(0, tk.END)
            if state.interval:
                entry_interval.insert(0, str(state.interval))
            entry_autostop.delete(0, tk.END)
            if state.auto_stop_after:
                entry_autostop.insert(0, _format_duration(state.auto_stop_after))
            _pad_imp = (state.schedule_blocks + [{}, {}, {}])[:3]
            for bi, (e_sh, e_sm, e_eh, e_em) in enumerate(block_entries):
                b = _pad_imp[bi]
                for e in (e_sh, e_sm, e_eh, e_em):
                    e.delete(0, tk.END)
                if "start" in b and b["start"]:
                    e_sh.insert(0, f"{b['start'][0]:02d}"); e_sm.insert(0, f"{b['start'][1]:02d}")
                    e_eh.insert(0, f"{b['end'][0]:02d}");   e_em.insert(0, f"{b['end'][1]:02d}")
            for i, v in enumerate(day_vars):
                v.set(i in state.schedule_days)
            theme_var.set(state.theme)
            hotkey_var.set(_format_hotkey(state.hotkey_mods, state.hotkey_vk))
            _pending_hotkey[0] = state.hotkey_mods
            _pending_hotkey[1] = state.hotkey_vk
            _refresh_listbox()
            save_settings()
            icon.update_menu()
            _apply_theme(style)
            notify(icon, T("Settings imported"))
        except Exception as e:
            messagebox.showerror(T("Import failed"), str(e), parent=root)

    exp_frame = ttk.Frame(tab_system)
    exp_frame.grid(row=20, column=0, sticky="w", padx=10, pady=(0, 14))
    ttk.Button(exp_frame, text=T("Export settings"), command=_export_settings).pack(side="left", padx=(0, 6))
    ttk.Button(exp_frame, text=T("Import settings"), command=_import_settings).pack(side="left")

    # ── Tab: Log ──────────────────────────────────────────────────
    tab_log = ttk.Frame(nb)
    nb.add(tab_log, text=T(" Log "))
    tab_log.columnconfigure(0, weight=1)
    tab_log.rowconfigure(0, weight=1)

    log_text = tk.Text(tab_log, width=54, height=14, state="disabled",
                       bg=ENTRY_BG, fg=FG, relief="flat", bd=1,
                       font=("Consolas", 9))
    log_scroll = ttk.Scrollbar(tab_log, command=log_text.yview)
    log_text.configure(yscrollcommand=log_scroll.set)
    log_text.grid(row=0, column=0, padx=(10, 0), pady=10, sticky="nsew")
    log_scroll.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ns")

    def _load_rows():
        if not os.path.exists(LOG_FILE):
            return []
        try:
            with open(LOG_FILE, newline="", encoding="utf-8") as lf:
                raw = list(_csv.reader(lf))
            if not raw:
                return []
            data_rows = raw[1:] if raw[0] == ["date", "start", "end", "duration_min"] else raw
            return [{"date": r[0], "start": r[1], "end": r[2], "duration_min": float(r[3])}
                    for r in data_rows if len(r) >= 4]
        except Exception:
            return []

    def _load_log():
        from collections import defaultdict
        log_text.configure(state="normal")
        log_text.delete("1.0", tk.END)
        rows = _load_rows()
        if not rows:
            log_text.insert(tk.END, T("No usage log yet."))
            log_text.configure(state="disabled")
            return
        by_date = defaultdict(list)
        for r in rows:
            by_date[r["date"]].append(r)
        total_all = 0.0
        for date in sorted(by_date.keys(), reverse=True):
            sessions = by_date[date]
            day_total = sum(float(r["duration_min"]) for r in sessions)
            total_all += day_total
            h, m = divmod(int(day_total), 60)
            log_text.insert(tk.END, f"── {date}  ({h}h {m:02d}m total) ──\n")
            for r in sessions:
                mins = float(r["duration_min"])
                if mins < 1:
                    dur_str = f"{int(mins * 60)}s"
                else:
                    h_s, m_s = divmod(int(mins), 60)
                    dur_str = f"{h_s}h {m_s:02d}m" if h_s else f"{m_s}m"
                log_text.insert(tk.END, f"  {r['start']} → {r['end']}  ({dur_str})\n")
            log_text.insert(tk.END, "\n")
        th, tm = divmod(int(total_all), 60)
        log_text.insert(tk.END, f"Total: {th}h {tm:02d}m across {len(rows)} sessions\n")
        log_text.configure(state="disabled")

    _load_log()

    _log_view_mode = ["list"]

    def _load_chart():
        from collections import defaultdict
        import datetime as _dt
        log_text.configure(state="normal")
        log_text.delete("1.0", tk.END)
        rows = _load_rows()
        if not rows:
            log_text.insert(tk.END, T("No usage log yet."))
            log_text.configure(state="disabled")
            return
        by_date = defaultdict(float)
        for r in rows:
            by_date[r["date"]] += r["duration_min"]
        today = _dt.date.today()
        dates = [(today - _dt.timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
        max_min = max((by_date.get(d, 0) for d in dates), default=1) or 1
        BAR_W = 24
        for d in reversed(dates):
            mins = by_date.get(d, 0)
            filled = int(round(mins / max_min * BAR_W))
            bar = "█" * filled + "░" * (BAR_W - filled)
            h, m = divmod(int(mins), 60)
            log_text.insert(tk.END, f"{d}  {bar}  {h}h {m:02d}m\n")
        log_text.configure(state="disabled")

    def _toggle_chart_view():
        if _log_view_mode[0] == "list":
            _log_view_mode[0] = "chart"
            _load_chart()
            chart_btn.configure(text="List")
        else:
            _log_view_mode[0] = "list"
            _load_log()
            chart_btn.configure(text="Chart")

    def _load_weekly():
        import datetime as _dt
        from collections import defaultdict
        rows = _load_rows()
        log_text.configure(state="normal")
        log_text.delete("1.0", tk.END)
        if not rows:
            log_text.insert(tk.END, T("No usage log yet."))
            log_text.configure(state="disabled")
            return
        by_week = defaultdict(list)
        for r in rows:
            d = _dt.date.fromisoformat(r["date"])
            iso = d.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            by_week[key].append(r)
        total_all = 0.0
        for week in sorted(by_week.keys(), reverse=True):
            sessions = by_week[week]
            week_total = sum(r["duration_min"] for r in sessions)
            total_all += week_total
            wh, wm = divmod(int(week_total), 60)
            days_active = len({r["date"] for r in sessions})
            avg_min = week_total / 7
            ah, am = divmod(int(avg_min), 60)
            avg_str = f"{ah}h {am:02d}m" if ah else f"{am}m"
            log_text.insert(tk.END, f"── {week}  ({wh}h {wm:02d}m total | {days_active}/7 days | avg/day {avg_str}) ──\n")
            by_date = defaultdict(float)
            for r in sessions:
                by_date[r["date"]] += r["duration_min"]
            for date in sorted(by_date.keys()):
                dh, dm = divmod(int(by_date[date]), 60)
                log_text.insert(tk.END, f"  {date}  {dh}h {dm:02d}m\n")
            log_text.insert(tk.END, "\n")
        th, tm = divmod(int(total_all), 60)
        log_text.insert(tk.END, f"Total: {th}h {tm:02d}m\n")
        log_text.configure(state="disabled")

    def _load_monthly():
        from collections import defaultdict
        rows = _load_rows()
        log_text.configure(state="normal")
        log_text.delete("1.0", tk.END)
        if not rows:
            log_text.insert(tk.END, T("No usage log yet."))
            log_text.configure(state="disabled")
            return
        by_month = defaultdict(list)
        for r in rows:
            key = r["date"][:7]
            by_month[key].append(r)
        total_all = 0.0
        for month in sorted(by_month.keys(), reverse=True):
            sessions = by_month[month]
            month_total = sum(r["duration_min"] for r in sessions)
            total_all += month_total
            mh, mm = divmod(int(month_total), 60)
            days_active = len({r["date"] for r in sessions})
            avg_min = month_total / 30
            ah, am = divmod(int(avg_min), 60)
            avg_str = f"{ah}h {am:02d}m" if ah else f"{am}m"
            log_text.insert(tk.END, f"── {month}  ({mh}h {mm:02d}m total | {days_active} days active | avg/day {avg_str}) ──\n")
            by_date = defaultdict(float)
            for r in sessions:
                by_date[r["date"]] += r["duration_min"]
            for date in sorted(by_date.keys()):
                dh, dm = divmod(int(by_date[date]), 60)
                log_text.insert(tk.END, f"  {date}  {dh}h {dm:02d}m\n")
            log_text.insert(tk.END, "\n")
        th, tm = divmod(int(total_all), 60)
        log_text.insert(tk.END, f"Total: {th}h {tm:02d}m\n")
        log_text.configure(state="disabled")

    def _set_log_view(mode):
        _log_view_mode[0] = mode
        chart_btn.configure(text=T("Chart") if mode != "chart" else T("List"))
        week_btn.configure(relief="sunken" if mode == "week" else "raised")
        month_btn.configure(relief="sunken" if mode == "month" else "raised")
        if mode == "list":       _load_log()
        elif mode == "chart":    _load_chart()
        elif mode == "week":     _load_weekly()
        elif mode == "month":    _load_monthly()

    def _export_html():
        import datetime as _dt
        from collections import defaultdict
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            parent=root, defaultextension=".html",
            filetypes=[("HTML files", "*.html")],
            initialfile="keep_awake_report.html",
            title="Export HTML report")
        if not path:
            return
        if not os.path.exists(LOG_FILE):
            messagebox.showinfo("Export HTML", T("No usage log yet."), parent=root)
            return
        try:
            with open(LOG_FILE, newline="", encoding="utf-8") as lf:
                raw = list(_csv.reader(lf))
            data_rows = raw[1:] if raw and raw[0] == ["date", "start", "end", "duration_min"] else raw
            rows = [{"date": r[0], "start": r[1], "end": r[2], "duration_min": float(r[3])}
                    for r in data_rows if len(r) >= 4]
        except Exception:
            rows = []
        by_date = defaultdict(list)
        for r in rows:
            by_date[r["date"]].append(r)
        today = _dt.date.today()
        dates = [(today - _dt.timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
        day_totals = {d: sum(r["duration_min"] for r in by_date.get(d, [])) for d in dates}
        max_min = max(day_totals.values(), default=1) or 1
        BAR_W = 30
        chart_lines = ""
        for d in reversed(dates):
            mins = day_totals.get(d, 0)
            filled = int(round(mins / max_min * BAR_W))
            bar = "█" * filled + "░" * (BAR_W - filled)
            h, m = divmod(int(mins), 60)
            chart_lines += f"{d}  {bar}  {h}h {m:02d}m\n"
        table_rows = ""
        for date in sorted(by_date.keys(), reverse=True):
            sessions = by_date[date]
            day_min = sum(r["duration_min"] for r in sessions)
            h, m = divmod(int(day_min), 60)
            for r in sessions:
                mins_r = r["duration_min"]
                if mins_r < 1:
                    dur_r = f"{int(mins_r * 60)}s"
                else:
                    h_r, m_r = divmod(int(mins_r), 60)
                    dur_r = f"{h_r}h {m_r:02d}m" if h_r else f"{m_r}m"
                table_rows += f"<tr><td>{r['date']}</td><td>{r['start']}</td><td>{r['end']}</td><td>{dur_r}</td></tr>\n"
            table_rows += f"<tr class='total'><td colspan='3'><b>{date} total</b></td><td><b>{h}h {m:02d}m</b></td></tr>\n"
        html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>Keep Awake — Usage Report</title>
<style>body{{font-family:monospace;margin:2em}}pre{{background:#1e1e1e;color:#ccc;padding:1em;border-radius:6px}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:6px 12px;text-align:left}}
th{{background:#f0f0f0}}.total{{background:#f9f9f9}}</style></head><body>
<h2>Keep Awake — Usage Report</h2>
<p>Generated: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<h3>Last 14 days</h3><pre>{chart_lines}</pre>
<h3>Sessions</h3><table><tr><th>Date</th><th>Start</th><th>End</th><th>Duration</th></tr>
{table_rows}</table></body></html>"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        os.startfile(path)

    log_btn_frame = ttk.Frame(tab_log)
    log_btn_frame.grid(row=1, column=0, columnspan=2, pady=(0, 8))

    def _clear_log():
        if not os.path.exists(LOG_FILE):
            return
        if messagebox.askyesno(T("Clear log_title"), T("Delete all usage history permanently?"), parent=root):
            with open(LOG_FILE, "w", encoding="utf-8"):
                pass
            _load_log()

    def _refresh_log():
        mode = _log_view_mode[0]
        if mode == "list":     _load_log()
        elif mode == "chart":  _load_chart()
        elif mode == "week":   _load_weekly()
        elif mode == "month":  _load_monthly()

    ttk.Button(log_btn_frame, text=T("Refresh"), command=_refresh_log).pack(side="left", padx=4)
    chart_btn = ttk.Button(log_btn_frame, text=T("Chart"),
                           command=lambda: _set_log_view("chart" if _log_view_mode[0] != "chart" else "list"))
    chart_btn.pack(side="left", padx=4)
    week_btn = ttk.Button(log_btn_frame, text=T("Week"),
                          command=lambda: _set_log_view("week" if _log_view_mode[0] != "week" else "list"))
    week_btn.pack(side="left", padx=4)
    month_btn = ttk.Button(log_btn_frame, text=T("Month"),
                           command=lambda: _set_log_view("month" if _log_view_mode[0] != "month" else "list"))
    month_btn.pack(side="left", padx=4)
    ttk.Button(log_btn_frame, text=T("Export HTML"), command=_export_html).pack(side="left", padx=4)
    ttk.Button(log_btn_frame, text=T("Open CSV"),
               command=lambda: os.startfile(LOG_FILE) if os.path.exists(LOG_FILE) else None).pack(side="left", padx=4)
    ttk.Button(log_btn_frame, text=T("Clear log"), command=_clear_log).pack(side="left", padx=4)

    # ── Save / Cancel ─────────────────────────────────────────────
    def apply(close=True):
        errors = []

        val_interval = entry_interval.get().strip()
        new_interval = None
        if val_interval:
            try:
                new_interval = int(val_interval)
                if new_interval < 10:
                    errors.append(T("Interval must be at least 10 seconds."))
            except ValueError:
                errors.append(T("Interval must be a number."))

        val_stop = entry_autostop.get().strip()
        new_autostop = None
        if val_stop:
            new_autostop, err = _parse_duration(val_stop)
            if err:
                errors.append(f"Auto-stop: {err}")
            elif new_autostop is None or new_autostop < 10:
                errors.append(T("Auto-stop must be at least 10 seconds."))

        # Validate time blocks
        new_blocks = []
        for bi, (e_sh, e_sm, e_eh, e_em) in enumerate(block_entries):
            sh_v = e_sh.get().strip(); sm_v = e_sm.get().strip()
            eh_v = e_eh.get().strip(); em_v = e_em.get().strip()
            if not any([sh_v, sm_v, eh_v, em_v]):
                continue
            try:
                sh = int(sh_v); sm = int(sm_v)
                eh = int(eh_v); em = int(em_v)
            except ValueError:
                errors.append(f"Block {bi+1}: {T('times must be numbers.')}")
                continue
            if not (0 <= sh <= 23 and 0 <= sm <= 59):
                errors.append(f"Block {bi+1}: {T('invalid start time.')}")
            elif not (0 <= eh <= 23 and 0 <= em <= 59):
                errors.append(f"Block {bi+1}: {T('invalid end time.')}")
            elif sh * 60 + sm >= eh * 60 + em:
                errors.append(f"Block {bi+1}: {T('start must be before end.')}")
            else:
                new_blocks.append({"start": [sh, sm], "end": [eh, em]})
        new_sched_check = sched_enabled_var.get()
        if new_sched_check and not new_blocks:
            errors.append(T("At least one time block is required when schedule is enabled."))

        new_days = {i for i, v in enumerate(day_vars) if v.get()}
        if new_sched_check and not new_days:
            errors.append(T("Select at least one day for the schedule."))

        if not keep_api_var.get() and not keep_mouse_var.get() and not keep_key_var.get():
            errors.append(T("At least one keep-awake method must be selected."))

        if errors:
            messagebox.showerror(T("Invalid settings"), "\n".join(errors), parent=root)
            return

        if new_interval is not None:
            state.interval = new_interval
        state.auto_stop_after = new_autostop
        if new_blocks:
            state.schedule_blocks = new_blocks
        state.schedule_days   = new_days
        state.theme           = theme_var.get()
        old_language          = state.language
        state.language        = language_var.get()

        # Apply schedule enabled state
        new_sched_enabled = sched_enabled_var.get()
        if new_sched_enabled and not state.schedule_enabled:
            state.schedule_enabled = True
            _start_schedule_thread(icon)
        elif not new_sched_enabled and state.schedule_enabled:
            state.schedule_enabled = False
            if state.running:
                _ka.stop_keeping(icon, None)

        # Apply hotkey if changed
        new_mods, new_vk = _pending_hotkey
        if new_mods != state.hotkey_mods or new_vk != state.hotkey_vk:
            state.hotkey_mods = new_mods
            state.hotkey_vk   = new_vk
            threading.Thread(target=_ka._reregister_hotkey, args=(icon,), daemon=True).start()

        # Apply Start with Windows
        if autostart_var.get():
            _ka.enable_autostart()
        else:
            _ka.disable_autostart()

        # Apply meeting detection
        state.meeting_detection = meeting_var.get()
        if state.meeting_detection:
            _start_meeting_monitor(icon)

        # Apply smart pause
        state.smart_pause = smart_pause_var.get()
        try:
            v = int(smart_pause_secs_var.get())
            state.smart_pause_secs = max(5, v)
        except ValueError:
            pass

        # Apply battery guard
        state.battery_guard = battery_guard_var.get()
        try:
            v = int(battery_threshold_var.get())
            state.battery_threshold = max(5, min(95, v))
        except ValueError:
            pass
        if state.battery_guard:
            _start_battery_monitor(icon)

        # Apply lock guard
        state.lock_guard = lock_guard_var.get()
        if state.lock_guard:
            _start_lock_monitor(icon)

        # Apply keep methods
        state.keep_api     = keep_api_var.get()
        state.keep_mouse   = keep_mouse_var.get()
        state.keep_key     = keep_key_var.get()
        state.nudge_key_vk = _pending_nudge_key[0]
        state.start_paused = start_paused_var.get()

        if state.running and state.auto_stop_after:
            _ka._schedule_auto_stop(icon, state.auto_stop_after)

        save_settings()
        icon.update_menu()
        icon.title = _build_tooltip()
        notify(icon, T("Settings saved"))
        language_changed = state.language != old_language
        if close or language_changed:
            root.destroy()
            if language_changed:
                threading.Thread(target=open_settings, args=(icon,), daemon=True).start()
        else:
            _apply_theme(style)

    frm_btn = ttk.Frame(root)
    frm_btn.pack(side="bottom", fill="x", pady=(0, 10))
    ttk.Button(frm_btn, text=T("Save"),   command=lambda: apply(close=True)).pack(side="left", padx=6)
    ttk.Button(frm_btn, text=T("Apply"),  command=lambda: apply(close=False)).pack(side="left", padx=6)
    ttk.Button(frm_btn, text=T("Cancel"), command=root.destroy).pack(side="left", padx=6)

    root.mainloop()
