# -*- coding: utf-8 -*-
"""
core.py — Pure logic: translations, duration helpers, schedule window check,
           tooltip builder, icon factory, ctypes helpers.

Imports only: state (no monitors, settings_ui, keep_awake).
"""

import ctypes
import ctypes.wintypes
import datetime
import re
import struct
import time

from state import state

# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------

_STRINGS = {
    "en": {
        "Start": "Start", "Stop": "Stop", "Interval": "Interval",
        "Auto-stop": "Auto-stop", "Profiles": "Profiles",
        "Settings": "Settings", "Changelog": "Changelog", "Quit": "Quit",
        "30 seconds": "30 seconds", "1 minute": "1 minute", "2 minutes": "2 minutes",
        "Custom": "Custom", "No limit": "No limit",
        "1 hour": "1 hour", "2 hours": "2 hours", "4 hours": "4 hours",
        "No profiles saved": "No profiles saved",
        "paused": "paused", "ACTIVE": "ACTIVE",
        "paused (in meeting)": "paused (in meeting)",
        "paused (low battery)": "paused (low battery)",
        "schedule enabled": "schedule enabled",
        "stops in": "stops in",
        "Keep Awake activated": "Keep Awake activated",
        "Keep Awake paused": "Keep Awake paused",
        "Meeting detected — Keep Awake paused": "Meeting detected — Keep Awake paused",
        "Meeting ended — Keep Awake resumed": "Meeting ended — Keep Awake resumed",
        "Charging — Keep Awake resumed": "Charging — Keep Awake resumed",
        "Settings saved": "Settings saved",
        "Settings exported": "Settings exported",
        "Settings imported": "Settings imported",
        "Profile activated": "Profile '{name}' activated",
        "Keep Awake — Settings": "Keep Awake — Settings",
        " General ": " General ", " Schedule ": " Schedule ",
        " Profiles ": " Profiles ", " System ": " System ", " Log ": " Log ",
        "Interval in seconds (blank = use quick menu selection)": "Interval in seconds (blank = use quick menu selection)",
        "Auto-stop (e.g. 1h30m, 20m, 45s — blank = no limit)": "Auto-stop (e.g. 1h30m, 20m, 45s — blank = no limit)",
        "Enable schedule": "Enable schedule",
        "Active days": "Active days",
        "Time blocks (up to 3)": "Time blocks (up to 3)",
        "Start_label": "Start", "End_label": "End",
        "Leave Start/End blank to skip a block.": "Leave Start/End blank to skip a block.",
        "Add current": "Add current", "Activate": "Activate",
        "Edit": "Edit", "Update": "Update", "Delete": "Delete",
        "Select a profile to see its settings.": "Select a profile to see its settings.",
        "'Add current' saves interval + auto-stop as a new profile.": "'Add current' saves interval + auto-stop as a new profile.",
        "Start with Windows": "Start with Windows",
        "Pause during Teams / Zoom meetings": "Pause during Teams / Zoom meetings",
        "Skip mouse nudge when user is active for less than": "Skip mouse nudge when user is active for less than",
        "seconds idle": "seconds idle",
        "Pause when battery below": "Pause when battery below",
        "Theme": "Theme", "Dark": "Dark", "Light": "Light",
        "Language": "Language", "English": "English", "Português": "Português",
        "Reset to defaults": "Reset to defaults",
        "Global hotkey (toggle)": "Global hotkey (toggle)",
        "Click then press a key combo": "Click then press a key combo",
        "Press a key combo…": "Press a key combo…",
        "Hold Ctrl/Shift/Alt, then press a letter": "Hold Ctrl/Shift/Alt, then press a letter",
        "Must include Ctrl, Shift, or Alt — try again": "Must include Ctrl, Shift, or Alt — try again",
        "Only letters A–Z are supported — try again": "Only letters A–Z are supported — try again",
        "Hotkey captured — click Apply/Save to activate": "Hotkey captured — click Apply/Save to activate",
        "Export settings": "Export settings", "Import settings": "Import settings",
        "Refresh": "Refresh", "Chart": "Chart", "List": "List",
        "Week": "Week", "Month": "Month", "Export HTML": "Export HTML",
        "Open CSV": "Open CSV", "Clear log": "Clear log",
        "No usage log yet.": "No usage log yet.",
        "Total:": "Total:", "across": "across", "sessions": "sessions",
        "Save": "Save", "Apply": "Apply", "Cancel": "Cancel",
        "New profile": "New profile", "Profile name:": "Profile name:",
        "Rename profile": "Rename profile", "New name:": "New name:",
        "Reset to defaults_title": "Reset to defaults",
        "Reset all settings to defaults?\nProfiles will be kept.": "Reset all settings to defaults?\nProfiles will be kept.",
        "Custom Interval": "Custom Interval",
        "Interval (e.g. 30, 90, 120 — seconds):": "Interval (e.g. 30, 90, 120 — seconds):",
        "Custom Auto-stop": "Custom Auto-stop",
        "Auto-stop (e.g. 1h30m, 20m, 45s — blank = no limit):": "Auto-stop (e.g. 1h30m, 20m, 45s — blank = no limit):",
        "Clear log_title": "Clear log",
        "Delete all usage history permanently?": "Delete all usage history permanently?",
        "Invalid settings": "Invalid settings",
        "Interval must be at least 10 seconds.": "Interval must be at least 10 seconds.",
        "Interval must be a number.": "Interval must be a number.",
        "Auto-stop must be at least 10 seconds.": "Auto-stop must be at least 10 seconds.",
        "Auto-stop: Use formats like: 1h30m, 20m, 45s, 90": "Auto-stop: Use formats like: 1h30m, 20m, 45s, 90",
        "times must be numbers.": "times must be numbers.",
        "invalid start time.": "invalid start time.",
        "invalid end time.": "invalid end time.",
        "start must be before end.": "start must be before end.",
        "At least one time block is required when schedule is enabled.": "At least one time block is required when schedule is enabled.",
        "Select at least one day for the schedule.": "Select at least one day for the schedule.",
        "Export failed": "Export failed", "Import failed": "Import failed",
        "Keep Awake is already running.\nCheck the system tray.": "Keep Awake is already running.\nCheck the system tray.",
        "Mon": "Mon", "Tue": "Tue", "Wed": "Wed", "Thu": "Thu",
        "Fri": "Fri", "Sat": "Sat", "Sun": "Sun",
        "Interval:": "Interval:", "Auto-stop:": "Auto-stop:", "Schedule:": "Schedule:",
        "on": "on", "off": "off",
        "Battery at % — Keep Awake paused": "Battery at {pct}% — Keep Awake paused",
        "Keep-awake methods": "Keep-awake methods",
        "System API (prevent sleep / screen off)": "System API (prevent sleep / screen off)",
        "Mouse nudge (move cursor 1px)": "Mouse nudge (move cursor 1px)",
        "Key press (Scroll Lock)": "Key press (Scroll Lock)",
        "Key press": "Key press",
        "Click then press a key (nudge)": "Click then press a key (nudge)",
        "At least one keep-awake method must be selected.": "At least one keep-awake method must be selected.",
        "Start paused (do not activate on launch)": "Start paused (do not activate on launch)",
        "Pause when screen is locked": "Pause when screen is locked",
        "Screen locked — Keep Awake paused": "Screen locked — Keep Awake paused",
        "Screen unlocked — Keep Awake resumed": "Screen unlocked — Keep Awake resumed",
    },
    "pt": {
        "Start": "Iniciar", "Stop": "Pausar", "Interval": "Intervalo",
        "Auto-stop": "Parar automaticamente", "Profiles": "Perfis",
        "Settings": "Configurações", "Changelog": "Histórico", "Quit": "Sair",
        "30 seconds": "30 segundos", "1 minute": "1 minuto", "2 minutes": "2 minutos",
        "Custom": "Personalizado", "No limit": "Sem limite",
        "1 hour": "1 hora", "2 hours": "2 horas", "4 hours": "4 horas",
        "No profiles saved": "Nenhum perfil salvo",
        "paused": "pausado", "ACTIVE": "ATIVO",
        "paused (in meeting)": "pausado (em reunião)",
        "paused (low battery)": "pausado (bateria fraca)",
        "schedule enabled": "agendamento ativo",
        "stops in": "para em",
        "Keep Awake activated": "Keep Awake ativado",
        "Keep Awake paused": "Keep Awake pausado",
        "Meeting detected — Keep Awake paused": "Reunião detectada — Keep Awake pausado",
        "Meeting ended — Keep Awake resumed": "Reunião encerrada — Keep Awake retomado",
        "Charging — Keep Awake resumed": "Carregando — Keep Awake retomado",
        "Settings saved": "Configurações salvas",
        "Settings exported": "Configurações exportadas",
        "Settings imported": "Configurações importadas",
        "Profile activated": "Perfil '{name}' ativado",
        "Keep Awake — Settings": "Keep Awake — Configurações",
        " General ": " Geral ", " Schedule ": " Agendamento ",
        " Profiles ": " Perfis ", " System ": " Sistema ", " Log ": " Log ",
        "Interval in seconds (blank = use quick menu selection)": "Intervalo em segundos (vazio = usar seleção do menu rápido)",
        "Auto-stop (e.g. 1h30m, 20m, 45s — blank = no limit)": "Parar após (ex: 1h30m, 20m, 45s — vazio = sem limite)",
        "Enable schedule": "Ativar agendamento",
        "Active days": "Dias ativos",
        "Time blocks (up to 3)": "Blocos de horário (até 3)",
        "Start_label": "Início", "End_label": "Fim",
        "Leave Start/End blank to skip a block.": "Deixe Início/Fim em branco para ignorar o bloco.",
        "Add current": "Adicionar atual", "Activate": "Ativar",
        "Edit": "Editar", "Update": "Atualizar", "Delete": "Excluir",
        "Select a profile to see its settings.": "Selecione um perfil para ver suas configurações.",
        "'Add current' saves interval + auto-stop as a new profile.": "'Adicionar atual' salva intervalo + parada automática como novo perfil.",
        "Start with Windows": "Iniciar com o Windows",
        "Pause during Teams / Zoom meetings": "Pausar durante reuniões no Teams / Zoom",
        "Skip mouse nudge when user is active for less than": "Não mover mouse quando usuário estiver ativo há menos de",
        "seconds idle": "segundos sem atividade",
        "Pause when battery below": "Pausar quando bateria abaixo de",
        "Theme": "Tema", "Dark": "Escuro", "Light": "Claro",
        "Language": "Idioma", "English": "English", "Português": "Português",
        "Reset to defaults": "Restaurar padrões",
        "Global hotkey (toggle)": "Atalho global (alternar)",
        "Click then press a key combo": "Clique e pressione uma combinação de teclas",
        "Press a key combo…": "Pressione uma combinação…",
        "Hold Ctrl/Shift/Alt, then press a letter": "Segure Ctrl/Shift/Alt e pressione uma letra",
        "Must include Ctrl, Shift, or Alt — try again": "Deve incluir Ctrl, Shift ou Alt — tente novamente",
        "Only letters A–Z are supported — try again": "Apenas letras A–Z são suportadas — tente novamente",
        "Hotkey captured — click Apply/Save to activate": "Atalho capturado — clique em Aplicar/Salvar para ativar",
        "Export settings": "Exportar configurações", "Import settings": "Importar configurações",
        "Refresh": "Atualizar", "Chart": "Gráfico", "List": "Lista",
        "Week": "Semana", "Month": "Mês", "Export HTML": "Exportar HTML",
        "Open CSV": "Abrir CSV", "Clear log": "Limpar log",
        "No usage log yet.": "Nenhum registro ainda.",
        "Total:": "Total:", "across": "em", "sessions": "sessões",
        "Save": "Salvar", "Apply": "Aplicar", "Cancel": "Cancelar",
        "New profile": "Novo perfil", "Profile name:": "Nome do perfil:",
        "Rename profile": "Renomear perfil", "New name:": "Novo nome:",
        "Reset to defaults_title": "Restaurar padrões",
        "Reset all settings to defaults?\nProfiles will be kept.": "Restaurar todas as configurações para o padrão?\nOs perfis serão mantidos.",
        "Custom Interval": "Intervalo personalizado",
        "Interval (e.g. 30, 90, 120 — seconds):": "Intervalo (ex: 30, 90, 120 — segundos):",
        "Custom Auto-stop": "Parada automática personalizada",
        "Auto-stop (e.g. 1h30m, 20m, 45s — blank = no limit):": "Parar após (ex: 1h30m, 20m, 45s — vazio = sem limite):",
        "Clear log_title": "Limpar log",
        "Delete all usage history permanently?": "Excluir todo o histórico de uso permanentemente?",
        "Invalid settings": "Configurações inválidas",
        "Interval must be at least 10 seconds.": "O intervalo deve ser de pelo menos 10 segundos.",
        "Interval must be a number.": "O intervalo deve ser um número.",
        "Auto-stop must be at least 10 seconds.": "A parada automática deve ser de pelo menos 10 segundos.",
        "Auto-stop: Use formats like: 1h30m, 20m, 45s, 90": "Parada automática: Use formatos como: 1h30m, 20m, 45s, 90",
        "times must be numbers.": "os horários devem ser números.",
        "invalid start time.": "horário de início inválido.",
        "invalid end time.": "horário de fim inválido.",
        "start must be before end.": "o início deve ser antes do fim.",
        "At least one time block is required when schedule is enabled.": "Pelo menos um bloco de horário é necessário quando o agendamento está ativo.",
        "Select at least one day for the schedule.": "Selecione pelo menos um dia para o agendamento.",
        "Export failed": "Falha na exportação", "Import failed": "Falha na importação",
        "Keep Awake is already running.\nCheck the system tray.": "Keep Awake já está em execução.\nVeja a bandeja do sistema.",
        "Mon": "Seg", "Tue": "Ter", "Wed": "Qua", "Thu": "Qui",
        "Fri": "Sex", "Sat": "Sáb", "Sun": "Dom",
        "Interval:": "Intervalo:", "Auto-stop:": "Parada auto:", "Schedule:": "Agendamento:",
        "on": "ativado", "off": "desativado",
        "Battery at % — Keep Awake paused": "Bateria em {pct}% — Keep Awake pausado",
        "Keep-awake methods": "Métodos de manutenção ativa",
        "System API (prevent sleep / screen off)": "API do sistema (evitar sleep / tela apagada)",
        "Mouse nudge (move cursor 1px)": "Mover mouse (1px)",
        "Key press (Scroll Lock)": "Pressionar tecla (Scroll Lock)",
        "Key press": "Pressionar tecla",
        "Click then press a key (nudge)": "Clique e pressione uma tecla (nudge)",
        "At least one keep-awake method must be selected.": "Pelo menos um método deve estar selecionado.",
        "Start paused (do not activate on launch)": "Iniciar pausado (não ativar ao abrir)",
        "Pause when screen is locked": "Pausar quando a tela estiver bloqueada",
        "Screen locked — Keep Awake paused": "Tela bloqueada — Keep Awake pausado",
        "Screen unlocked — Keep Awake resumed": "Tela desbloqueada — Keep Awake retomado",
    },
}


def T(key):
    """Translate *key* using state.language."""
    return _STRINGS.get(state.language, _STRINGS["en"]).get(key, key)


# ---------------------------------------------------------------------------
# ctypes structs
# ---------------------------------------------------------------------------

class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


class _SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus",        ctypes.c_byte),
        ("BatteryFlag",         ctypes.c_byte),
        ("BatteryLifePercent",  ctypes.c_byte),
        ("SystemStatusFlag",    ctypes.c_byte),
        ("BatteryLifeTime",     ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


# ---------------------------------------------------------------------------
# Duration helpers
# ---------------------------------------------------------------------------

def _parse_duration(val: str):
    val = val.strip().lower()
    if not val:
        return None, None
    pattern = re.fullmatch(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', val)
    if pattern and any(pattern.groups()):
        h = int(pattern.group(1) or 0)
        m = int(pattern.group(2) or 0)
        s = int(pattern.group(3) or 0)
        return h * 3600 + m * 60 + s, None
    try:
        return int(val), None
    except ValueError:
        return None, "Use formats like: 1h30m, 20m, 45s, 90"


def _format_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s   = divmod(rem, 60)
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s: parts.append(f"{s}s")
    return "".join(parts) or "0s"


# ---------------------------------------------------------------------------
# Schedule window check (pure — receives state as parameter)
# ---------------------------------------------------------------------------

def _in_schedule_window(st=None):
    """Return True if current time falls inside one of state's schedule blocks.

    Accepts an explicit *st* AppState for testing; defaults to the global state.
    """
    if st is None:
        st = state
    now = datetime.datetime.now()
    if now.weekday() not in st.schedule_days:
        return False
    t = now.hour * 60 + now.minute
    return any(
        b["start"][0] * 60 + b["start"][1] <= t < b["end"][0] * 60 + b["end"][1]
        for b in st.schedule_blocks
    )


# ---------------------------------------------------------------------------
# Tooltip builder (pure — receives state as parameter)
# ---------------------------------------------------------------------------

def _build_tooltip(st=None):
    """Build the tray icon tooltip string.

    Accepts an explicit *st* AppState for testing; defaults to the global state.
    """
    if st is None:
        st = state
    if st.meeting_active:
        return f"Keep Awake — {T('paused (in meeting)')}"
    if st.battery_paused:
        pct = _get_battery_percent()
        pct_str = f" ({pct}%)" if pct is not None else ""
        return f"Keep Awake — {T('paused (low battery)')}{pct_str}"
    if not st.running or st.active_since is None:
        sched_str = f" | {T('schedule enabled')}" if st.schedule_enabled else ""
        return f"Keep Awake — {T('paused')}{sched_str}"
    elapsed = int(time.monotonic() - st.active_since)
    h, m = divmod(elapsed // 60, 60)
    elapsed_str = f"{h}h {m:02d}m" if h else f"{m}m"
    limit_str = ""
    if st.auto_stop_after:
        remaining = max(0, st.auto_stop_after - elapsed)
        rh, rm = divmod(remaining // 60, 60)
        limit_str = f" | {T('stops in')} {rh}h {rm:02d}m" if rh else f" | {T('stops in')} {rm}m"
    sched_str = f" | {T('schedule enabled')}" if st.schedule_enabled else ""
    return f"Keep Awake — {T('ACTIVE')} ({elapsed_str}{limit_str}{sched_str})"


# ---------------------------------------------------------------------------
# System helpers
# ---------------------------------------------------------------------------

def _get_idle_secs():
    lii = _LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(lii)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) / 1000.0


def _get_battery_percent():
    sps = _SYSTEM_POWER_STATUS()
    ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps))
    if sps.ACLineStatus == 1:         # plugged in
        return None
    if sps.BatteryLifePercent > 100:  # no battery / unknown
        return None
    return sps.BatteryLifePercent


# ---------------------------------------------------------------------------
# Icon factory
# ---------------------------------------------------------------------------

def _make_icon_image(active: bool):
    SIZE = 64
    pixels = bytearray(SIZE * SIZE * 4)  # RGBA, top-down

    def _set(x, y, r, g, b, a=255):
        if 0 <= x < SIZE and 0 <= y < SIZE:
            i = (y * SIZE + x) * 4
            pixels[i], pixels[i+1], pixels[i+2], pixels[i+3] = r, g, b, a

    def _ellipse(x0, y0, x1, y1, r, g, b):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
        for py in range(y0, y1 + 1):
            for px in range(x0, x1 + 1):
                if rx > 0 and ry > 0:
                    if ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1.0:
                        _set(px, py, r, g, b)

    h_ = "#00CC66" if active else "#CC0000"
    cr, cg, cb = int(h_[1:3], 16), int(h_[3:5], 16), int(h_[5:7], 16)
    _ellipse(8,  8,  56, 56, cr, cg, cb)
    _ellipse(16, 22, 30, 42, 255, 255, 255)
    _ellipse(34, 22, 48, 42, 255, 255, 255)
    _ellipse(20, 28, 26, 36, 0,   0,   0)
    _ellipse(38, 28, 44, 36, 0,   0,   0)

    # Win32 LoadImage requires bottom-up DIB and an AND mask appended after XOR pixels.
    # Convert top-down RGBA -> bottom-up BGRA
    bgra = bytearray(SIZE * SIZE * 4)
    for row in range(SIZE):
        src_row = row
        dst_row = SIZE - 1 - row  # flip vertically
        for col in range(SIZE):
            s = (src_row * SIZE + col) * 4
            d = (dst_row * SIZE + col) * 4
            bgra[d+0] = pixels[s+2]  # B
            bgra[d+1] = pixels[s+1]  # G
            bgra[d+2] = pixels[s+0]  # R
            bgra[d+3] = pixels[s+3]  # A

    # AND mask: 1-bit per pixel, bottom-up, row-padded to 4-byte boundary.
    # All zeros = fully opaque (alpha channel in XOR data handles transparency).
    row_bytes = ((SIZE + 31) // 32) * 4  # rows padded to DWORD
    and_mask = bytes(row_bytes * SIZE)

    # BITMAPINFOHEADER — biHeight is SIZE*2 for ICO (XOR + AND mask combined)
    bih = struct.pack("<IiiHHIIiiII",
        40,           # biSize
        SIZE,         # biWidth
        SIZE * 2,     # biHeight = height*2 signals XOR+AND layout to LoadImage
        1,            # biPlanes
        32,           # biBitCount
        0,            # biCompression BI_RGB
        0,            # biSizeImage
        0, 0, 0, 0)

    img_data = bih + bytes(bgra) + and_mask

    ico_header = struct.pack("<HHH", 0, 1, 1)
    img_offset = 6 + 16
    dir_entry  = struct.pack("<BBBBHHII",
        SIZE, SIZE, 0, 0, 1, 32, len(img_data), img_offset)
    ico_bytes  = ico_header + dir_entry + img_data

    class _IcoImage:
        def save(self, fp, format=None, **kwargs):
            if hasattr(fp, "write"):
                fp.write(ico_bytes)
            else:
                with open(fp, "wb") as f:
                    f.write(ico_bytes)

    return _IcoImage()


_ICON_ACTIVE   = None
_ICON_INACTIVE = None


def make_icon(active: bool):
    global _ICON_ACTIVE, _ICON_INACTIVE
    if active:
        if _ICON_ACTIVE is None:
            _ICON_ACTIVE = _make_icon_image(True)
        return _ICON_ACTIVE
    else:
        if _ICON_INACTIVE is None:
            _ICON_INACTIVE = _make_icon_image(False)
        return _ICON_INACTIVE


# ---------------------------------------------------------------------------
# Hotkey formatter
# ---------------------------------------------------------------------------

MOD_CONTROL = 0x0002
MOD_SHIFT   = 0x0004
MOD_ALT     = 0x0001
MOD_WIN     = 0x0008

_MOD_NAMES = {MOD_CONTROL: "Ctrl", MOD_SHIFT: "Shift", MOD_ALT: "Alt", MOD_WIN: "Win"}


def _format_hotkey(mods, vk):
    parts = [name for bit, name in sorted(_MOD_NAMES.items()) if mods & bit]
    char = chr(vk) if 0x41 <= vk <= 0x5A else f"0x{vk:02X}"
    parts.append(char)
    return "+".join(parts)


# ---------------------------------------------------------------------------
# Dark mode helper (reads state.theme — kept here for use by settings_ui)
# ---------------------------------------------------------------------------

def _is_dark_mode():
    return state.theme == "dark"
