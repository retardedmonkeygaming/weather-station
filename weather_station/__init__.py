"""
Weather Station Core Package
A professional, multi-surface weather station system.
"""

__version__ = "2.0.0"
__author__ = "Weather Station Team"

from .core.app_state import AppState
from .core.events import EventSystem, EventType
from .config.settings import SettingsManager, SettingDefinition
from .db.database import DatabaseManager

__all__ = [
    "AppState",
    "EventSystem",
    "EventType",
    "SettingsManager",
    "SettingDefinition",
    "DatabaseManager",
]