"""
logging_setup.py — application logging with rotation and levels.

Feature (ENH 1): proper Python `logging` with:
    * console handler (INFO by default, human-friendly format)
    * rotating file handler (5 MB per file, 5 backups) writing DEBUG+
    * per-module levels via logger names (weather.main, weather.api, ...)
    * LOG_LEVEL env override; LOG_FILE env override for the file path

Called once from main.run() before any subsystem starts.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

import config

_FMT_CONSOLE = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_FMT_FILE = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"

_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _coerce_level(name: str, fallback: int) -> int:
    return _LEVELS.get(str(name).strip().upper(), fallback)


def setup_logging() -> None:
    """Configure the root 'weather' logger tree once at startup."""
    root = logging.getLogger("weather")
    if getattr(root, "_weather_configured", False):
        return

    console_level = _coerce_level(config.LOG_LEVEL, logging.INFO)

    root.setLevel(logging.DEBUG)          # handlers do the filtering
    fmt_console = logging.Formatter(_FMT_CONSOLE, datefmt="%H:%M:%S")
    fmt_file = logging.Formatter(_FMT_FILE)

    # Console — honors LOG_LEVEL
    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(fmt_console)
    root.addHandler(console)

    # Rotating file — always DEBUG for post-mortem diagnostics
    try:
        Path(config.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt_file)
        root.addHandler(file_handler)
        root._weather_configured = True
        root.info(
            "Logging configured — console=%s, file=%s (5MB x 5, DEBUG)",
            logging.getLevelName(console_level), config.LOG_FILE,
        )
    except OSError as exc:
        # e.g. read-only filesystem: console logging still works
        root._weather_configured = True
        root.warning("Rotating file logging disabled: %s", exc)


def set_console_level(name: str) -> bool:
    """Runtime log-level switch (settings DB / API). Returns success."""
    level = _coerce_level(name, -1)
    if level < 0:
        return False
    root = logging.getLogger("weather")
    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.handlers.RotatingFileHandler):
            handler.setLevel(level)
    return True
