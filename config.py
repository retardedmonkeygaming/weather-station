"""
config.py — centralized configuration & shared runtime state.

Owns:
    * Hardware pin mapping (BCM numbering) for LCD, DHT11, button, buzzer.
    * Global constants (LCD geometry, thresholds, supervision, paths).
    * Settings defaults + validation tables (single source of truth).
    * API endpoint builders for Open-Meteo weather & air-quality services.
    * Environment detection (Pi vs desktop) for mock hardware fallbacks.
    * AppState: the one mutable shared-state object every module reads/writes.
    * Subsystem health map used by the supervisor and surfaced on the web UI.
"""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

APP_VERSION = "5.2"

# ---------------------------------------------------------------------------
# .env loading (tiny dependency-free parser, called once at import)
# ---------------------------------------------------------------------------

# Project root is the repo root itself (flat layout, no package wrapper).
_PROJECT_ROOT = Path(__file__).resolve().parent


def load_dotenv(path: Optional[Path] = None) -> Dict[str, str]:
    """Parse KEY=VALUE lines into os.environ (existing env wins)."""
    env_path = Path(path) if path else _PROJECT_ROOT / ".env"
    loaded: Dict[str, str] = {}
    if not env_path.exists():
        return loaded
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            loaded[key] = value
    return loaded


load_dotenv()


def _env_int(name: str, fallback: Optional[int] = None) -> Optional[int]:
    raw = os.environ.get(name)
    if raw is None:
        return fallback
    try:
        return int(re.sub(r"[^0-9]", "", raw) or fallback)
    except (TypeError, ValueError):
        return fallback


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def is_raspberry_pi() -> bool:
    """True when running on a Pi (GPIO device tree present), else desktop."""
    return os.path.exists("/proc/device-tree/model")


# Evaluated once at import; drivers branch on this for real/mock hardware.
IS_PI = is_raspberry_pi()

# First frame pushed to the LCD in desktop/mock mode.
MOCK_BOOT_MESSAGE = "SIMULATED"

# ---------------------------------------------------------------------------
# Hardware pin map (BCM numbering) — env-overridable (.env / setup wizard)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PinConfig:
    # HD44780 1602A in 4-bit mode
    LCD_RS: int = 21
    LCD_EN: int = 17
    LCD_D4: int = 25
    LCD_D5: int = 24
    LCD_D6: int = 23
    LCD_D7: int = 18
    # Sensors & actuators
    DHT_PIN: int = 4
    BUTTON_PIN: int = 27
    BUZZER_PIN: int = 2
    # Optional PWM contrast pin (1602A V0) for Guest Mode dimming
    LCD_CONTRAST_PIN: Optional[int] = None
    # Where these values came from: 'env' (wizard/.env) or 'defaults'
    source: str = "defaults"


# Frozen singleton consumed by drivers & main wiring.
# Any LCD_RS/LCD_EN/... env var present (setup wizard writes these) wins.
PIN = PinConfig(
    LCD_RS=_env_int("LCD_RS", 22),
    LCD_EN=_env_int("LCD_EN", 17),
    LCD_D4=_env_int("LCD_D4", 25),
    LCD_D5=_env_int("LCD_D5", 24),
    LCD_D6=_env_int("LCD_D6", 23),
    LCD_D7=_env_int("LCD_D7", 18),
    DHT_PIN=_env_int("DHT_PIN", 4),
    BUTTON_PIN=_env_int("BUTTON_PIN", 27),
    BUZZER_PIN=_env_int("BUZZER_PIN", 2),
    LCD_CONTRAST_PIN=_env_int("LCD_CONTRAST_PIN", None),
    source="env" if os.environ.get("LCD_RS") else "defaults",
)

# Discord bot token (optional; captured by the first-run setup wizard)
DISCORD_BOT_TOKEN: Optional[str] = os.environ.get("DISCORD_BOT_TOKEN") or None

# Discord live updates (optional): post a weather card to this channel ID
# every time the data changes (rate-limited by MIN_INTERVAL).
DISCORD_UPDATE_CHANNEL_ID: Optional[int] = (
    _env_int("DISCORD_UPDATE_CHANNEL_ID", 0) or None
)
DISCORD_UPDATE_MIN_INTERVAL_S = int(
    os.environ.get("DISCORD_UPDATE_MIN_INTERVAL_S", "60")
)

# Discord permission gate (optional): members holding this role name may use
# admin commands. Guild administrators always pass.
DISCORD_ADMIN_ROLE: Optional[str] = os.environ.get("DISCORD_ADMIN_ROLE") or None

# ---------------------------------------------------------------------------
# LCD design-system constants (STRICT 1602A geometry)
# ---------------------------------------------------------------------------

LCD_COLUMNS = 16
LCD_ROWS = 2

# CGRAM slots 0x00-0x07 (8 user-definable 5x8 glyphs)
LCD_CUSTOM_CHAR_SLOTS = 8

# Guest Mode contrast levels (duty cycle for the optional V0 PWM pin)
LCD_CONTRAST_FULL = 0.85
LCD_CONTRAST_DIM = 0.25

# Custom glyphs burned in ONCE at startup and never recreated at runtime:
# HD44780 CGRAM rewrites bank all eight slots and can glitch an in-flight
# frame. Slot 0x07 therefore carries a STATIC moon glyph; the phase itself is
# communicated as text (see services/moon_phase.py).
CUSTOM_CHARACTERS: Dict[int, list] = {
    0x00: [31, 17, 10, 4, 10, 21, 31, 0],   # Hourglass frame 1
    0x01: [31, 21, 4, 10, 17, 17, 31, 0],   # Hourglass frame 2
    0x02: [4, 14, 14, 14, 31, 31, 4, 0],    # Alarm bell
    0x03: [0, 10, 0, 4, 17, 14, 0, 0],      # Smile
    0x04: [0, 14, 31, 31, 31, 14, 0, 0],    # Cloud
    0x05: [4, 21, 14, 31, 14, 21, 4, 0],    # Sun
    0x06: [31, 31, 31, 31, 31, 31, 31, 31],  # Loading block
    0x07: [0, 14, 31, 31, 31, 14, 0, 0],    # Moon glyph (static, burn-once)
}

MOON_GLYPH_SLOT = 0x07

# ---------------------------------------------------------------------------
# Location / service endpoints
# ---------------------------------------------------------------------------

DEFAULT_LATITUDE = "29.325390"
DEFAULT_LONGITUDE = "48.019562"

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AQI_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

HTTP_TIMEOUT_SECONDS = 8.0

# Guest Mode: LCD auto-dims & buzzer silences after this much button inactivity
GUEST_MODE_TIMEOUT_S = 30 * 60

# Screen Timeout (ENH 6): blank the LCD after this many idle seconds while
# the screen setting is ON. 0 disables. Overridable per-install via .env and
# at runtime via the settings DB ("screen_timeout").
SCREEN_TIMEOUT_S = _env_int("SCREEN_TIMEOUT_S", 30) or 0

# Logging (ENH 1)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.environ.get("LOG_FILE", str(_PROJECT_ROOT / "weather_station.log"))

# Web dashboard basic auth (ENH 2). Enabled by default with admin/admin;
# change WEB_AUTH_USERNAME / WEB_AUTH_PASSWORD in .env or set
# WEB_AUTH_ENABLED=OFF to disable. /api/health stays open for liveness probes.
WEB_AUTH_ENABLED = os.environ.get("WEB_AUTH_ENABLED", "ON").strip().upper() in (
    "ON", "1", "TRUE", "YES",
)
WEB_AUTH_USERNAME = os.environ.get("WEB_AUTH_USERNAME", "admin")
WEB_AUTH_PASSWORD = os.environ.get("WEB_AUTH_PASSWORD", "admin")

# Historical log compression (ENH 3): gzip-archive rows older than this many
# days into logs_archive/ when the compress_logs setting is ON.
LOGS_ARCHIVE_DIR = _PROJECT_ROOT / "logs_archive"
LOG_ARCHIVE_AFTER_DAYS = _env_int("LOG_ARCHIVE_AFTER_DAYS", 30) or 30

# Voice Mode: announce temperature shifts of at least this many degrees C
VOICE_TEMP_DELTA_C = 2.0

# MQTT publishing (optional; set MQTT_BROKER in .env to enable)
MQTT_BROKER = os.environ.get("MQTT_BROKER", "")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "weatherstation")
MQTT_INTERVAL_S = int(os.environ.get("MQTT_INTERVAL_S", "60"))


def build_api_urls(latitude: str, longitude: str) -> tuple:
    """Return (forecast_url, aqi_url) for Open-Meteo given coordinates."""
    forecast = (
        f"{OPEN_METEO_FORECAST_URL}"
        f"?latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,relative_humidity_2m,weather_code,uv_index"
        "&daily=temperature_2m_max,temperature_2m_min,uv_index_max&timezone=auto"
    )
    aqi = (
        f"{OPEN_METEO_AQI_URL}"
        f"?latitude={latitude}&longitude={longitude}"
        "&current=us_aqi,pm10,pm2_5"
    )
    return forecast, aqi


# ---------------------------------------------------------------------------
# Defaults & limits
# ---------------------------------------------------------------------------

DB_FILE = os.environ.get(
    "WEATHER_DB_PATH",
    str(_PROJECT_ROOT / "weather_history.db"),
)
HOST = os.environ.get("WEATHER_HOST", "0.0.0.0")
PORT = int(os.environ.get("WEATHER_PORT", "8000"))

BOOT_TEMP_HIGH_THRESHOLD = 32.0   # deg C
BOOT_TEMP_LOW_THRESHOLD = 10.0    # deg C

# Supervision / recovery
TASK_RESTART_COOLDOWN_S = 5.0

# Settings option cycles (mirrors the physical button settings menu)
SETTING_OPTION_CYCLES: Dict[str, list] = {
    "unit": ["C", "F"],
    "buzzer": ["ALL", "ERR", "MUTE"],
    "screen": ["ON", "OFF"],
    "auto_scroll": [0, 3, 5, 10],
    "alarm_on": ["ON", "OFF"],
    "api_rate": [5, 10, 15],
    "log_rate": [5, 15, 30],
}

MAX_LCD_PAGES = 10
BASE_PAGE_COUNT = 6

# User-visible page names (designer tabs; page_meta table overrides)
PAGE_NAMES: Dict[int, str] = {
    1: "Clock", 2: "Indoor", 3: "Outdoor", 4: "Forecast",
    5: "Air Quality", 6: "Moon", 7: "Extra 1", 8: "Extra 2",
    9: "Extra 3", 10: "Extra 4",
}

SETTINGS_DEFAULTS: Dict[str, Any] = {
    "unit": "C",          # [1] C / F
    "buzzer": "ALL",      # [2] ALL / ERR / MUTE
    "screen": "ON",       # [3] ON / OFF
    "auto_scroll": 0,     # [4] 0 (Off) / 3 / 5 / 10 s
    "alarm_on": "OFF",    # [5] ON / OFF
    "alarm_hr": 17,       # [6] 0-23
    "alarm_min": 0,       # [7] 0-55 (step 5)
    "api_rate": 10,       # [8] 5 / 10 / 15 min
    "log_rate": 15,       # [9] 5 / 15 / 30 min
    "dht_offset_temp": 0.0,
    "latitude": DEFAULT_LATITUDE,
    "longitude": DEFAULT_LONGITUDE,
    "voice_mode": "OFF",  # web-only toggle: speak temps on tap / big shifts
    "guest_mode": "OFF",  # web-only toggle: dim + silence after idle
    "alert_high": BOOT_TEMP_HIGH_THRESHOLD,   # Discord /set-alert + DHT alerts
    "alert_low": BOOT_TEMP_LOW_THRESHOLD,
    "screen_timeout": 30,  # seconds of idle before LCD blanks (0 = off)
    "compress_logs": "OFF",  # ON: gzip-archive log rows > 30 days old
}

# Type coercion map used when loading settings from the DB
SETTINGS_TYPES: Dict[str, type] = {
    "auto_scroll": int,
    "alarm_hr": int,
    "alarm_min": int,
    "api_rate": int,
    "log_rate": int,
    "dht_offset_temp": float,
    "alert_high": float,
    "alert_low": float,
    "screen_timeout": int,
}


# ---------------------------------------------------------------------------
# Subsystem health (supervisor <-> web UI)
# ---------------------------------------------------------------------------

_subsystem_health: Dict[str, Dict[str, Any]] = {}
_health_lock = threading.Lock()


def register_subsystem_failure(name: str, exc: Exception) -> None:
    """Record a subsystem failure; surfaced via /api/health & /api/data."""
    with _health_lock:
        prev = _subsystem_health.get(name, {})
        _subsystem_health[name] = {
            "failed_at": time.time(),
            "error": str(exc) or exc.__class__.__name__,
            "restarts": prev.get("restarts", 0) + 1,
        }


def mark_subsystem_healthy(name: str) -> None:
    with _health_lock:
        _subsystem_health.pop(name, None)


def subsystem_status() -> Dict[str, Dict[str, Any]]:
    """Snapshot of currently failing subsystems (empty dict = all healthy)."""
    with _health_lock:
        return {name: dict(info) for name, info in _subsystem_health.items()}


# ---------------------------------------------------------------------------
# Notification center (web UI bell icon)
# ---------------------------------------------------------------------------

_NOTIFICATION_LIMIT = 50
_notifications: List[Dict[str, Any]] = []
_notif_lock = threading.Lock()


def push_notification(kind: str, message: str) -> None:
    """Record a notification for the bell icon.

    kind: 'alert' (temp alerts) | 'alarm' | 'error' | 'info'
    Newest first, capped at _NOTIFICATION_LIMIT entries.
    """
    with _notif_lock:
        _notifications.insert(0, {
            "ts": time.time(),
            "kind": kind,
            "message": message,
        })
        del _notifications[_NOTIFICATION_LIMIT:]


def get_notifications(limit: int = 25) -> List[Dict[str, Any]]:
    with _notif_lock:
        return [dict(n) for n in _notifications[:limit]]


def clear_notifications() -> None:
    with _notif_lock:
        _notifications.clear()


# ---------------------------------------------------------------------------
# Shared runtime state (single mutable object, guard for cross-thread writes)
# ---------------------------------------------------------------------------

@dataclass
class AppState:
    """The one mutable shared-state object every module reads/writes.

    All background tasks and FastAPI routes share one asyncio loop, so plain
    attribute access is safe; `_lock` exists for callers that touch state from
    secondary threads (e.g. gpiozero button callbacks).
    """

    # Navigation
    current_page: int = 1
    total_pages: int = BASE_PAGE_COUNT
    page_changed: bool = True

    # Indoor climate (DHT11)
    indoor_temp: Optional[float] = None
    indoor_temp_raw: Optional[float] = None
    indoor_humid: Optional[float] = None
    dht_error: bool = False

    # Outdoor climate (Open-Meteo)
    outdoor_temp: str = "N/A"
    outdoor_humid: str = "N/A"
    outdoor_min: str = "N/A"
    outdoor_max: str = "N/A"
    uv_current: str = "N/A"
    uv_max: str = "N/A"
    weather_code: int = 0
    wifi_error: bool = False

    # Air quality
    aqi_val: str = "N/A"
    aqi_status: str = "N/A"
    pm2_5_val: str = "N/A"
    pm10_val: str = "N/A"

    # Diagnostics & alerts
    override_active: bool = False
    temp_alert_active: bool = False
    temp_alert_msg: str = ""
    temp_trend_symbol: str = "->"

    # Historical temp tracking (ring buffer of (timestamp, temp))
    temp_history_tracker: list = field(default_factory=list)

    # Graceful-shutdown snapshot bookkeeping
    started_at: float = field(default_factory=time.time)

    # Guest Mode (idle dimming) & Voice Mode bookkeeping
    last_button_press: float = field(default_factory=time.time)
    guest_active: bool = False
    last_spoken_temp: Optional[float] = None

    # Screen Timeout (ENH 6): True while the LCD is blanked on idle
    screen_blank: bool = False

    # Alarm
    alarm_ringing: bool = False
    alarm_dismissed_today: bool = False
    clock_icon_frame: str = "\x00"

    # Physical settings-menu session (triple-tap mode)
    in_settings_mode: bool = False
    settings_index: int = 1
    total_settings: int = 10

    # UI Designer mappings {page_id: widget_type}
    custom_lcd_pages: Dict[int, str] = field(default_factory=dict)

    # User-assigned page tab names {page_id: name}
    page_names: Dict[int, str] = field(default_factory=dict)

    # LCD mirror of what is physically rendered (for web dashboard display)
    last_lcd_rendered_text: list = field(default_factory=lambda: ["", ""])

    # Settings (loaded from DB over defaults at boot)
    settings: Dict[str, Any] = field(
        default_factory=lambda: dict(SETTINGS_DEFAULTS)
    )

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    # -- convenience accessors -------------------------------------------

    def get_setting(self, key: str) -> Any:
        with self._lock:
            return self.settings.get(key, SETTINGS_DEFAULTS.get(key))

    def set_setting(self, key: str, value: Any) -> None:
        with self._lock:
            self.settings[key] = value

    def clean_settings(self) -> Dict[str, Any]:
        """Public settings snapshot without internal _subsys_* keys."""
        with self._lock:
            return {k: v for k, v in self.settings.items()
                    if not k.startswith("_")}

    def mark_page_dirty(self) -> None:
        """Flag the display loop that the current page needs a re-render."""
        self.page_changed = True


# Module-level singleton shared by every subsystem
state = AppState()


def get_state() -> AppState:
    """Access the shared runtime state singleton."""
    return state
