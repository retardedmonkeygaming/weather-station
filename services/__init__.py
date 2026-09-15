"""
services/ — network integrations, pure calculations, widget rendering, bot.
"""

from services.moon_phase import calculate_moon_phase
from services.render import WIDGET_CATALOG, WIDGET_REGISTRY
from services import discord_bot

__all__ = [
    "calculate_moon_phase",
    "WIDGET_CATALOG",
    "WIDGET_REGISTRY",
    "discord_bot",
]
