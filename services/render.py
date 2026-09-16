"""
render.py — widget -> 16x2 frame rendering engine.

Owns:
    * The widget registry: every predefined widget maps to a pure function
      (state -> (line1, line2)), each designed for exactly 16x2 chars.
    * Custom layout JSON blocks: {"type":"custom","lines":[...]} strings allow
      user-authored frames; they pass through the same geometry validation.
    * Frame composition priority: temp alerts > alarm > settings mode >
      custom/default page layouts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Callable, Dict, Optional, Tuple

import config
from config import get_state
from services import moon_phase
from services.weather_api import weather_info
from utils import (
    format_temp, format_humid, get_comfort_level, scroll_label, safe_float,
    clip_text, center_text,
)

log = logging.getLogger("weather.render")

Frame = Tuple[str, str]

LCD_COLS = config.LCD_COLUMNS

# ---------------------------------------------------------------------------
# Predefined widgets (each returns a Frame engineered for 16 cols x 2 rows)
# ---------------------------------------------------------------------------

def _compact_temp(c_temp, unit: str, cols: int = 5) -> str:
    """format_temp, shortened until it fits `cols` chars.

    Normal temps ("23.5C" / "74.3F") pass through untouched; only extreme
    values ("-40.0F", "257.0F") degrade to whole degrees so LCD lines stay
    within 16 columns without relying on the driver's hard clip.
    """
    s = format_temp(c_temp, unit)
    while len(s) > cols and "." in s:
        s = f"{float(s[:-1]):.0f}{s[-1]}"
    return s


def _pm(v) -> str:
    """Particulate value as a compact int string ('999' / 'N/A')."""
    try:
        return str(int(float(v)))
    except (TypeError, ValueError):
        return "N/A"


def widget_clock(_state) -> Frame:
    state = get_state()
    now = datetime.now()
    # Centered time & date (user request: the clock page looked empty because
    # both lines hugged the left edge). Alarm bell keeps its glyph slot.
    alarm = state.get_setting("alarm_on") == "ON"
    time_s = ("\x02 " if alarm else "") + now.strftime("%H:%M:%S")
    line1 = center_text(time_s, LCD_COLS)
    line2 = center_text(now.strftime("%d-%m-%Y"), LCD_COLS)
    return line1, line2


def widget_indoor(_state) -> Frame:
    state = get_state()
    if state.dht_error:
        return "In: ERR [DHT11]", "State: Check"
    unit = state.get_setting("unit")
    # Worst case fits 16: "In:-40F-> H:100%" — compact temp keeps headroom.
    line1 = (f"In:{_compact_temp(state.indoor_temp, unit)}"
             f"{state.temp_trend_symbol} H:{format_humid(state.indoor_humid)}")
    line2 = f"State: {get_comfort_level(state.indoor_temp, state.indoor_humid)} \x03"
    return line1, line2


def widget_outdoor(_state) -> Frame:
    state = get_state()
    unit = state.get_setting("unit")
    humid = safe_float(state.outdoor_humid)
    h_out = f"{int(humid)}%" if humid is not None else "N/A"
    w_icon, w_text = weather_info(state.weather_code)
    # "*"/"!" = station offline (full word would overflow worst case); the
    # status page and web dashboard spell it out.
    flag = "*" if state.wifi_error else ""
    line1 = f"Out:{_compact_temp(state.outdoor_temp, unit)} {h_out}{flag}"
    line2 = f"Fcst: {w_icon} {w_text}{'!' if state.wifi_error else ''}"
    return line1, line2


def widget_forecast(_state) -> Frame:
    state = get_state()
    unit = state.get_setting("unit")
    flag = "!" if state.wifi_error else ""
    line1 = (f"L:{_compact_temp(state.outdoor_min, unit)} "
             f"H:{_compact_temp(state.outdoor_max, unit)}{flag}")
    line2 = f"UV:{state.uv_current} Max:{state.uv_max}"
    return line1, line2


def widget_aqi(_state) -> Frame:
    state = get_state()
    # Engineered for 16 cols: "AQI:999 Sensitiv" = 16 exactly (max label 8)
    line1 = f"AQI:{state.aqi_val} {state.aqi_status}"
    flag = "!" if state.wifi_error else ""
    # Worst case fits 16: "P25:999 P10:999!"
    line2 = f"P25:{_pm(state.pm2_5_val)} P10:{_pm(state.pm10_val)}{flag}"
    return line1, line2


def widget_pm(_state) -> Frame:
    state = get_state()
    return (f"PM2.5:{state.pm2_5_val}ug/m3",
            f"PM10:{state.pm10_val} ug/m3")


def widget_moon(_state) -> Frame:
    _, short_p, illum, _ = moon_phase.calculate_moon_phase()
    # Glyph + short phase name: "\x07 Wax Crescent" = 14 cols (fits any phase)
    return f"\x07 {short_p}", f"Illum: {illum}%"


def widget_humidity(_state) -> Frame:
    state = get_state()
    return f"Humidity: {format_humid(state.indoor_humid)}", "Indoor Air Damp"


def widget_uv(_state) -> Frame:
    state = get_state()
    return f"UV Index: {state.uv_current}", f"UV Peak: {state.uv_max}"


def widget_comfort(_state) -> Frame:
    state = get_state()
    unit = state.get_setting("unit")
    line1 = (f"In:{format_temp(state.indoor_temp, unit)} "
             f"H:{format_humid(state.indoor_humid)}")
    line2 = f"State: {get_comfort_level(state.indoor_temp, state.indoor_humid)} \x03"
    return line1, line2


def widget_status(_state) -> Frame:
    state = get_state()
    d_st = "ERR" if state.dht_error else "OK"
    w_st = "ERR" if state.wifi_error else "OK"
    return f"DHT:{d_st}  WiFi:{w_st}", "Station Active"


def widget_pi(_state) -> Frame:
    stats = get_pi_system_stats()
    return (f"CPU:{stats['cpu_temp']} {stats['cpu_usage']}",
            f"RAM:{stats['ram_usage']}")


def get_pi_system_stats() -> Dict[str, str]:
    """Pi diagnostics read from /proc & thermal zones (desktop-safe)."""
    cpu_temp = cpu_usage = ram_usage = "N/A"
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            cpu_temp = f"{float(f.read().strip()) / 1000.0:.1f}C"
    except Exception:
        pass
    try:
        with open("/proc/stat") as f:
            fields = [float(c) for c in f.readline().strip().split()[1:]]
            idle, total = fields[3], sum(fields)
            cpu_usage = f"{100.0 * (1.0 - idle / total):.1f}%"
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
            mem_total = int(lines[0].split()[1])
            mem_available = int(lines[2].split()[1])
            ram_usage = f"{100.0 * (1.0 - mem_available / mem_total):.1f}%"
    except Exception:
        pass
    return {"cpu_temp": cpu_temp, "cpu_usage": cpu_usage,
            "ram_usage": ram_usage}


WIDGET_REGISTRY: Dict[str, Callable[[object], Frame]] = {
    "widget_clock": widget_clock,
    "widget_indoor": widget_indoor,
    "widget_outdoor": widget_outdoor,
    "widget_forecast": widget_forecast,
    "widget_aqi": widget_aqi,
    "widget_pm": widget_pm,
    "widget_moon": widget_moon,
    "widget_humidity": widget_humidity,
    "widget_uv": widget_uv,
    "widget_comfort": widget_comfort,
    "widget_status": widget_status,
    "widget_pi": widget_pi,
}

# Designer catalog metadata (consumed by web/templates/designer.html)
WIDGET_CATALOG = [
    {"type": "widget_clock",    "icon": "🕒", "title": "Digital Clock",
     "desc": "Real-time clock & date"},
    {"type": "widget_indoor",   "icon": "🌡️", "title": "Indoor Climate",
     "desc": "Indoor temp & humidity"},
    {"type": "widget_outdoor",  "icon": "☀️", "title": "Outdoor Weather",
     "desc": "Outdoor conditions now"},
    {"type": "widget_forecast", "icon": "📅", "title": "Weather Forecast",
     "desc": "Daily min/max + UV (cached in Local Mode)"},
    {"type": "widget_aqi",      "icon": "🍃", "title": "Air Quality",
     "desc": "US AQI score & status"},
    {"type": "widget_pm",       "icon": "🌫️", "title": "Air Pollutants",
     "desc": "PM2.5 & PM10 levels"},
    {"type": "widget_moon",     "icon": "🌙", "title": "Moon Phase",
     "desc": "Phase & illumination"},
    {"type": "widget_humidity", "icon": "💧", "title": "Humidity Gauge",
     "desc": "Indoor humidity level"},
    {"type": "widget_uv",       "icon": "🔆", "title": "UV Index",
     "desc": "Current & max UV"},
    {"type": "widget_comfort",  "icon": "😊", "title": "Comfort Level",
     "desc": "Indoor comfort index"},
    {"type": "widget_status",   "icon": "⚡", "title": "Diagnostics",
     "desc": "Sensor & WiFi status"},
    {"type": "widget_pi",       "icon": "🤖", "title": "Pi System",
     "desc": "CPU temp, load & RAM"},
]


def render_widget_page(widget_type: str) -> Optional[Frame]:
    """Render any registered widget; custom JSON blocks handled separately."""
    renderer = WIDGET_REGISTRY.get(widget_type)
    if renderer is None:
        return None
    try:
        return renderer(get_state())
    except Exception:
        log.exception("Widget %s render failed", widget_type)
        return None


# ---------------------------------------------------------------------------
# Custom layout JSON blocks
# ---------------------------------------------------------------------------

def render_custom_layout(layout_json: str) -> Optional[Frame]:
    """Render a user-authored {"type":"custom","lines":[l1,l2]} block.

    Lines are honored verbatim; the LCD facade still clips to 16 cols.
    """
    try:
        data = json.loads(layout_json)
        lines = data.get("lines", [])
        if not isinstance(lines, list) or not lines:
            return None
        line1 = str(lines[0])
        line2 = str(lines[1]) if len(lines) > 1 else ""
        return line1, line2
    except (json.JSONDecodeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Settings-mode frame (physical button menu)
# ---------------------------------------------------------------------------

_SETTINGS_FRAMES = {
    1:  lambda s: ("1. Temp Unit",    f"> Mode: [{s.get_setting('unit')}]"),
    2:  lambda s: ("2. Buzzer Mode",  f"> Sound: [{s.get_setting('buzzer')}]"),
    3:  lambda s: ("3. Screen Power", f"> Power: [{s.get_setting('screen')}]"),
    4:  lambda s: ("4. Auto Scroll",
                   f"> Rotate: [{scroll_label(int(s.get_setting('auto_scroll')))}]"),
    5:  lambda s: ("5. Daily Alarm",  f"> State: [{s.get_setting('alarm_on')}]"),
    6:  lambda s: ("6. Alarm Hour",   f"> Hour: [{int(s.get_setting('alarm_hr')):02d}]"),
    7:  lambda s: ("7. Alarm Minute", f"> Mins: [{int(s.get_setting('alarm_min')):02d}]"),
    8:  lambda s: ("8. API Interval", f"> Rate: [{int(s.get_setting('api_rate'))}m]"),
    9:  lambda s: ("9. Log Interval", f"> Rate: [{int(s.get_setting('log_rate'))}m]"),
    10: lambda s: ("10.Factory Reset", "> HOLD 3S RESET"),
}


def _settings_frame(state) -> Frame:
    builder = _SETTINGS_FRAMES.get(state.settings_index)
    if builder is None:
        return "Settings", "Out of range"
    return builder(state)


# ---------------------------------------------------------------------------
# Default page layouts (pages 1-6 without designer assignments)
# ---------------------------------------------------------------------------

DEFAULT_PAGE_LAYOUT: Dict[int, str] = {
    1: "widget_clock",
    2: "widget_indoor",
    3: "widget_outdoor",
    4: "widget_forecast",
    5: "widget_aqi",
    6: "widget_moon",
}


def _default_widget_for(page_id: int) -> str:
    return DEFAULT_PAGE_LAYOUT.get(page_id, "widget_indoor")


# ---------------------------------------------------------------------------
# Frame composition (the heart of the display loop)
# ---------------------------------------------------------------------------

def build_frame(state) -> Frame:
    """Compose the current LCD frame by priority: alerts > alarm > settings
    > custom/default pages. Returns two <=16-char lines (LCD enforces)."""
    if state.temp_alert_active:
        return _split_alert(state.temp_alert_msg)

    if state.alarm_ringing:
        hr = int(state.get_setting("alarm_hr"))
        mn = int(state.get_setting("alarm_min"))
        return "\x02 ALARM TRIGGER ", f"Time: {hr:02d}:{mn:02d}"

    if state.in_settings_mode:
        return _settings_frame(state)

    # Designer-assigned page (custom JSON or predefined widget)
    assignment = state.custom_lcd_pages.get(state.current_page)
    if assignment:
        frame = render_custom_layout(assignment) or render_widget_page(assignment)
        if frame:
            return frame

    # Default layout
    frame = render_widget_page(_default_widget_for(state.current_page))
    return frame if frame else ("", "")


def _split_alert(msg: str) -> Frame:
    """Split an alert message into two rows, clipped to 16 cols each."""
    lines = msg.split("\n")
    return clip_text(lines[0], LCD_COLS), clip_text(
        lines[1] if len(lines) > 1 else "", LCD_COLS)
