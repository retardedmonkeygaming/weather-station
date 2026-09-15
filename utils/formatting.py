"""
formatting.py — small pure formatting helpers (no state access, no I/O).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


# ---------------------------------------------------------------------------
# STRICT 1602A geometry helpers (16 columns — no wrap-around, ever)
# ---------------------------------------------------------------------------

def clip_text(text: str, length: int = 16) -> str:
    """Hard-clip a string to `length` chars (HD44780 rows never wrap)."""
    return str(text)[:length]


def pad_text(text: str, length: int = 16) -> str:
    """Right-pad a string to exactly `length` chars with spaces."""
    text = str(text)
    return text + " " * max(0, length - len(text))


def center_text(text: str, length: int = 16) -> str:
    """Center a string inside exactly `length` chars, clipped if longer."""
    return str(text).center(length)[:length]


def format_temp(c_temp, unit: str = "C") -> str:
    """Unit-aware temperature string ('23.5C' / '74.3F' / 'N/A')."""
    if c_temp is None or c_temp == "N/A":
        return "N/A"
    try:
        val = float(c_temp)
    except (TypeError, ValueError):
        return "N/A"
    if unit == "F":
        return f"{(val * 9 / 5) + 32:.1f}F"
    return f"{val:.1f}C"


def format_humid(humid) -> str:
    """Humidity string ('45%' or 'N/A')."""
    if isinstance(humid, (int, float)):
        return f"{humid}%"
    return "N/A"


def get_comfort_level(temp_c, humid) -> str:
    """Comfort classification used on LCD page 2 & the dashboard."""
    if temp_c is None or humid is None:
        return "Unknown"
    if temp_c > 29:
        return "Hot"
    if humid < 30:
        return "Dry"
    if humid > 65:
        return "Humid"
    if 20 <= temp_c <= 26 and 30 <= humid <= 60:
        return "Comfort"
    return "Moderate"


def temp_formatter(unit: str):
    """Return a one-arg formatter bound to a unit ('C' or 'F')."""
    def fmt(c_temp) -> str:
        return format_temp(c_temp, unit)
    return fmt


def safe_float(value) -> Optional[float]:
    """float(value) or None — for 'N/A' strings coming from the API state."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def scroll_label(value: int) -> str:
    """'3s' / 'OFF' for the settings menu auto-scroll row."""
    return f"{value}s" if value > 0 else "OFF"


def next_in_cycle(options: list, current: Any) -> Any:
    """Next value in a settings cycle list (wraps, falls back to first)."""
    try:
        i = options.index(current)
    except ValueError:
        return options[0]
    return options[(i + 1) % len(options)]


def is_night_time(now: Optional[datetime] = None) -> bool:
    """Quiet hours: 23:00-07:00 — buzzer suppressed unless forced."""
    if now is None:
        now = datetime.now()
    return now.hour >= 23 or now.hour < 7
