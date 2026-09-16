"""
config_io.py — first-run setup wizard persistence.

Owns:
    * first_run_needed(): whether the guided wizard should be shown.
    * save_setup(): persist wizard input to .env and patch config.py.
    * ensure_directories(): auto-create the project layout.

Design notes:
    * Pins are written to .env (LCD_RS=.., DHT_PIN=..) which config.py reads
      at import — the wizard's choices take effect on the next start.
    * config.py is ALSO patched so the values are visible as code defaults
      (belt and braces; keeps the file human-editable afterwards).
    * Everything the wizard writes is idempotent: re-running the wizard
      updates existing lines in place.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, Optional

import config

log = logging.getLogger("weather.setup")

# Project root is the repo root itself (flat layout, no package wrapper).
_PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = _PROJECT_ROOT / ".env"
CONFIG_FILE = _PROJECT_ROOT / "config.py"

# Keys managed by the wizard (pin mapping + optional integrations)
ENV_KEYS = [
    "LCD_RS", "LCD_EN", "LCD_D4", "LCD_D5", "LCD_D6", "LCD_D7",
    "DHT_PIN", "BUTTON_PIN", "BUZZER_PIN",
    "DISCORD_BOT_TOKEN",
    "DISCORD_UPDATE_CHANNEL_ID", "DISCORD_ADMIN_ROLE",
    "DISCORD_WEATHER_IMAGE_URL", "DISCORD_REMINDER_CHANNEL_ID",
]

def _config_target() -> Path:
    """config.py lives beside this module in the flat root layout."""
    pkg = config.__file__
    if pkg:
        return Path(pkg).resolve()
    return CONFIG_FILE


# ---------------------------------------------------------------------------
# First-run detection
# ---------------------------------------------------------------------------

def first_run_needed() -> bool:
    """True when the setup wizard should run.

    Heuristic: no .env with any LCD pin definition => first run. A .env
    created by the wizard always contains at least LCD_RS=..
    """
    if not ENV_FILE.exists():
        return True
    try:
        content = ENV_FILE.read_text(encoding="utf-8")
    except OSError:
        return True
    return "LCD_RS=" not in content


# ---------------------------------------------------------------------------
# Directory scaffolding
# ---------------------------------------------------------------------------

def ensure_directories() -> None:
    """Create the expected flat root layout if any piece is missing."""
    for sub in ("hardware", "services", "utils", "web", "web/templates"):
        (_PROJECT_ROOT / sub).mkdir(parents=True, exist_ok=True)
    log.debug("Directory structure verified under %s", _PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _upsert_env(env_path: Path, updates: Dict[str, str]) -> None:
    """Write KEY=VALUE pairs into .env, updating existing keys in place."""
    lines: list = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    existing = {}
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if m:
            existing[m.group(1)] = i

    for key, value in updates.items():
        if key in existing:
            lines[existing[key]] = f"{key}={value}"
        else:
            lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _patch_config_constants(updates: Dict[str, str]) -> None:
    """Patch pin defaults + version marker in config.py (best effort)."""
    target = _config_target()
    if not target.exists():
        log.warning("config.py not found at %s — skipping patch", target)
        return

    text = target.read_text(encoding="utf-8")

    for key in ENV_KEYS:
        if key.startswith("DISCORD_"):
            continue  # secrets/optional keys live in .env only, never in code
        value = updates.get(key)
        if value is None:
            continue
        # class PinConfig: LCD_RS: int = 22  -> LCD_RS: int = <new>
        pattern = rf"({key}:\s*int\s*=\s*)(\d+)"
        text = re.sub(pattern, rf"\g<1>{value}", text, count=1)

    target.write_text(text, encoding="utf-8")


def save_setup(pins: Dict[str, int],
               discord_token: Optional[str] = None,
               discord_channel_id: Optional[str] = None,
               discord_admin_role: Optional[str] = None,
               discord_image_url: Optional[str] = None,
               discord_reminder_channel_id: Optional[str] = None) -> Dict[str, str]:
    """Persist wizard results: .env always; config.py patched as a mirror.

    Returns the sanitized .env content actually written (token masked).
    """
    updates: Dict[str, str] = {k: str(v) for k, v in pins.items()}
    if discord_token:
        updates["DISCORD_BOT_TOKEN"] = discord_token
    if discord_channel_id:
        updates["DISCORD_UPDATE_CHANNEL_ID"] = discord_channel_id
    if discord_admin_role:
        updates["DISCORD_ADMIN_ROLE"] = discord_admin_role
    if discord_image_url:
        updates["DISCORD_WEATHER_IMAGE_URL"] = discord_image_url
    if discord_reminder_channel_id:
        updates["DISCORD_REMINDER_CHANNEL_ID"] = discord_reminder_channel_id

    ensure_directories()
    _upsert_env(ENV_FILE, updates)
    try:
        _patch_config_constants(updates)
    except Exception:
        log.exception("config.py patch failed — .env still authoritative")

    masked = dict(updates)
    if "DISCORD_BOT_TOKEN" in masked:
        masked["DISCORD_BOT_TOKEN"] = "***hidden***"
    log.info("Setup saved to %s (%d keys)", ENV_FILE, len(updates))
    return masked
