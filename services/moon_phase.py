"""
moon_phase.py — isolated moon tracking mathematics.

Pure functions only: no I/O, no shared state, trivially testable.
Formula preserved verbatim from the original monolith.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional, Tuple

# Synodic month reference: known new moon 2000-01-06 18:14 UTC
_REF_EPOCH = datetime(2000, 1, 6, 18, 14)
_SYNODIC_MONTH = 29.5305877057

# (upper_bound_days, phase_name, short_name) — short names fit a 16-col LCD
_PHASE_TABLE: Tuple[Tuple[float, str, str], ...] = (
    (1.84566,  "New Moon",         "New Moon"),
    (5.53699,  "Waxing Crescent",  "Wax Crescent"),
    (9.22831,  "First Quarter",    "1st Quarter"),
    (12.91963, "Waxing Gibbous",   "Wax Gibbous"),
    (16.61096, "Full Moon",        "Full Moon"),
    (20.30228, "Waning Gibbous",   "Wan Gibbous"),
    (23.99361, "Last Quarter",     "3rd Quarter"),
    (27.68493, "Waning Crescent",  "Wan Crescent"),
)


def moon_age(dt: Optional[datetime] = None) -> float:
    """Days since the last new moon (0 .. 29.53)."""
    if dt is None:
        dt = datetime.now()
    days = (dt - _REF_EPOCH).total_seconds() / 86400.0
    return days % _SYNODIC_MONTH


def illumination(dt: Optional[datetime] = None) -> int:
    """Percent of the lunar disc illuminated (0-100)."""
    age = moon_age(dt)
    fraction = age / _SYNODIC_MONTH
    return round((1 - math.cos(fraction * 2 * math.pi)) / 2 * 100)


def phase_name(dt: Optional[datetime] = None) -> Tuple[str, str]:
    """(full_name, short_name) for the current phase."""
    age = moon_age(dt)
    for upper, full, short in _PHASE_TABLE:
        if age < upper:
            return full, short
    return "New Moon", "New Moon"


def calculate_moon_phase(
    dt: Optional[datetime] = None,
) -> Tuple[str, str, int, float]:
    """Convenience bundle: (full_name, short_name, illumination_pct, age).

    Preserves the original monolith's return contract exactly.
    """
    full, short = phase_name(dt)
    return full, short, illumination(dt), round(moon_age(dt), 1)
