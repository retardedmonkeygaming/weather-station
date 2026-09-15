"""
voice.py — Voice Mode (optional) using espeak (subprocess) or pyttsx3.

Announcements:
    * On a physical button tap (short beep replaced by a spoken summary).
    * When indoor temperature changes by >= VOICE_TEMP_DELTA_C (2.0) since the
      last announcement.

Design:
    * Synthesis runs in a daemon thread so the async loop never blocks.
    * espeak is tried first (`espeak <text>`); pyttsx3 is the fallback; if
      neither exists the engine no-ops quietly (desktop-safe).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from typing import Optional

import config
from config import get_state
from utils import format_humid, format_temp

log = logging.getLogger("weather.voice")

_espeak_path: Optional[str] = shutil.which("espeak")
_pyttsx3 = None
_init_attempted = False
_engine_lock = threading.Lock()


def _get_pyttsx3():
    """Lazy pyttsx3 import (only when espeak is missing)."""
    global _pyttsx3, _init_attempted
    if _pyttsx3 is not None or _init_attempted:
        return _pyttsx3
    _init_attempted = True
    try:
        import pyttsx3
        _pyttsx3 = pyttsx3
    except ImportError:
        _pyttsx3 = None
    return _pyttsx3


def _speak_blocking(text: str) -> None:
    """Blocking TTS call — always invoked from the worker thread."""
    if _espeak_path:
        try:
            subprocess.run(
                [_espeak_path, "-v", "en+f3", "-s", "150", text],
                capture_output=True, timeout=15,
            )
            return
        except Exception:
            log.exception("espeak failed")
    engine_mod = _get_pyttsx3()
    if engine_mod is not None:
        try:
            engine = engine_mod.init()
            engine.say(text)
            engine.runAndWait()
            return
        except Exception:
            log.exception("pyttsx3 failed")


def speak(text: str) -> None:
    """Fire-and-forget speech in a daemon thread (never blocks the loop)."""
    threading.Thread(target=_speak_blocking, args=(text,),
                     daemon=True, name="voice-tts").start()


def is_configured() -> bool:
    """True when any TTS backend is available (drives the settings hint)."""
    return bool(_espeak_path) or _get_pyttsx3() is not None


def announce_summary() -> None:
    """Spoken indoor/outdoor summary — hooked to the button tap."""
    state = get_state()
    unit = state.get_setting("unit")
    parts = [f"Indoor {format_temp(state.indoor_temp, unit)}"]
    if state.outdoor_temp != "N/A":
        parts.append(f"Outdoor {format_temp(state.outdoor_temp, unit)}")
    parts.append(f"Humidity {format_humid(state.indoor_humid)}")
    speak(". ".join(parts))


def maybe_announce_temp_change() -> None:
    """Speak when indoor temp moved >= 2.0C since the last announcement."""
    state = get_state()
    if state.indoor_temp is None:
        return
    last = state.last_spoken_temp
    if last is not None and abs(state.indoor_temp - last) >= config.VOICE_TEMP_DELTA_C:
        direction = "up" if state.indoor_temp > last else "down"
        speak(f"Temperature has gone {direction} to "
              f"{state.indoor_temp:.1f} degrees")
        state.last_spoken_temp = state.indoor_temp
    elif last is None:
        state.last_spoken_temp = state.indoor_temp
