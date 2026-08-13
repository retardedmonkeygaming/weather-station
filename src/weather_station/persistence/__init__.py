"""
Persistence module: Database layer with repository pattern
SQLAlchemy models, migrations, and data access
"""

from .models import Base, Setting, SensorLog, AlertLog, DiscordServerConfig, DiscordUserConfig, UpdateCheck, SystemEvent
from .database import DatabaseManager, get_database_manager

__all__ = [
    'Base', 'Setting', 'SensorLog', 'AlertLog', 
    'DiscordServerConfig', 'DiscordUserConfig', 
    'UpdateCheck', 'SystemEvent',
    'DatabaseManager', 'get_database_manager'
]
