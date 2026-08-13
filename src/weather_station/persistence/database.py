"""
Database Manager with repository pattern
Handles all database operations, migrations, and retention policies
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy import select, delete, func

from .models import Base, Setting, SensorLog, AlertLog, DiscordServerConfig, DiscordUserConfig, UpdateCheck, SystemEvent


class DatabaseManager:
    """
    Central database manager with repository pattern.
    Provides thin data-access layer over SQLAlchemy.
    """
    
    def __init__(self, database_url: str = "sqlite+aiosqlite:///./data/skycast.db"):
        self.database_url = database_url
        self.engine: Optional[AsyncEngine] = None
        self.session_maker: Optional[async_sessionmaker] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize database connection and create tables"""
        try:
            # Ensure data directory exists
            db_path = Path(self.database_url.replace("sqlite+aiosqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create engine
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                future=True
            )
            
            # Create session maker
            self.session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self._initialized = True
            print(f"[DatabaseManager] Initialized: {self.database_url}")
            return True
            
        except Exception as e:
            print(f"[DatabaseManager] Initialization failed: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
        self._initialized = False
        print("[DatabaseManager] Shutdown complete")
    
    async def get_session(self) -> AsyncSession:
        """Get a database session"""
        if not self.session_maker:
            raise RuntimeError("Database not initialized")
        return self.session_maker()
    
    # ========== Settings Repository ==========
    
    async def get_setting(self, key: str) -> Optional[Setting]:
        """Get a setting by key"""
        async with await self.get_session() as session:
            result = await session.execute(select(Setting).where(Setting.key == key))
            return result.scalar_one_or_none()
    
    async def get_setting_value(self, key: str, default: Any = None) -> Any:
        """Get setting value with type conversion"""
        setting = await self.get_setting(key)
        if setting:
            return setting.get_typed_value()
        return default
    
    async def set_setting(
        self,
        key: str,
        value: Any,
        value_type: str = 'string',
        changed_by: str = 'system',
        user_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Setting:
        """Set or update a setting"""
        async with await self.get_session() as session:
            # Check if exists
            result = await session.execute(select(Setting).where(Setting.key == key))
            setting = result.scalar_one_or_none()
            
            if setting:
                # Update existing
                setting.value = str(value) if value_type != 'json' else json.dumps(value)
                setting.value_type = value_type
                setting.last_changed_by = changed_by
                setting.changed_by_user_id = user_id
                if description:
                    setting.description = description
            else:
                # Create new
                setting = Setting(
                    key=key,
                    value=str(value) if value_type != 'json' else json.dumps(value),
                    value_type=value_type,
                    last_changed_by=changed_by,
                    changed_by_user_id=user_id,
                    description=description
                )
                session.add(setting)
            
            await session.commit()
            await session.refresh(setting)
            return setting
    
    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as dictionary"""
        async with await self.get_session() as session:
            result = await session.execute(select(Setting))
            settings = result.scalars().all()
            return {s.key: s.to_dict() for s in settings}
    
    async def export_settings(self) -> str:
        """Export all settings as JSON"""
        settings = await self.get_all_settings()
        return json.dumps(settings, indent=2)
    
    async def import_settings(self, json_data: str, changed_by: str = 'import') -> int:
        """Import settings from JSON, returns count of imported settings"""
        settings_dict = json.loads(json_data)
        count = 0
        for key, data in settings_dict.items():
            await self.set_setting(
                key=key,
                value=data.get('value'),
                value_type=data.get('value_type', 'string'),
                changed_by=changed_by
            )
            count += 1
        return count
    
    async def factory_reset_settings(self, keep_logs: bool = True) -> None:
        """Reset all settings to defaults, optionally keeping logs"""
        async with await self.get_session() as session:
            # Delete non-system settings
            await session.execute(delete(Setting).where(Setting.is_system == False))
            await session.commit()
        
        if not keep_logs:
            await self.clear_old_logs(days=0)
    
    # ========== Sensor Logs Repository ==========
    
    async def log_sensor_data(
        self,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        pressure: Optional[float] = None,
        aqi: Optional[int] = None,
        aqi_status: Optional[str] = None,
        feels_like: Optional[float] = None,
        station_id: str = 'default',
        source: str = 'api'
    ) -> SensorLog:
        """Log sensor data"""
        async with await self.get_session() as session:
            log = SensorLog(
                temperature=temperature,
                humidity=humidity,
                pressure=pressure,
                aqi=aqi,
                aqi_status=aqi_status,
                feels_like=feels_like,
                station_id=station_id,
                source=source
            )
            session.add(log)
            await session.commit()
            await session.refresh(log)
            return log
    
    async def get_recent_sensor_logs(
        self,
        hours: int = 24,
        station_id: str = 'default'
    ) -> List[SensorLog]:
        """Get recent sensor logs"""
        async with await self.get_session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            result = await session.execute(
                select(SensorLog)
                .where(SensorLog.timestamp >= cutoff)
                .where(SensorLog.station_id == station_id)
                .order_by(SensorLog.timestamp.desc())
            )
            return list(result.scalars().all())
    
    async def clear_old_logs(self, days: int = 30) -> int:
        """Clear logs older than specified days, returns deleted count"""
        async with await self.get_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                delete(SensorLog).where(SensorLog.timestamp < cutoff)
            )
            deleted = result.rowcount
            await session.commit()
            return deleted
    
    # ========== Alert Logs Repository ==========
    
    async def log_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = 'warning',
        value: Optional[float] = None,
        threshold: Optional[float] = None,
        station_id: str = 'default'
    ) -> AlertLog:
        """Log an alert"""
        async with await self.get_session() as session:
            alert = AlertLog(
                alert_type=alert_type,
                message=message,
                severity=severity,
                value=value,
                threshold=threshold,
                station_id=station_id
            )
            session.add(alert)
            await session.commit()
            await session.refresh(alert)
            return alert
    
    # ========== Discord Config Repository ==========
    
    async def get_discord_server_config(self, guild_id: str) -> Optional[DiscordServerConfig]:
        """Get Discord server config"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(DiscordServerConfig).where(DiscordServerConfig.guild_id == guild_id)
            )
            return result.scalar_one_or_none()
    
    async def upsert_discord_server_config(
        self,
        guild_id: str,
        **kwargs
    ) -> DiscordServerConfig:
        """Create or update Discord server config"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(DiscordServerConfig).where(DiscordServerConfig.guild_id == guild_id)
            )
            config = result.scalar_one_or_none()
            
            if config:
                for key, value in kwargs.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            else:
                config = DiscordServerConfig(guild_id=guild_id, **kwargs)
                session.add(config)
            
            await session.commit()
            await session.refresh(config)
            return config
    
    async def get_discord_user_config(self, user_id: str) -> Optional[DiscordUserConfig]:
        """Get Discord user config"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(DiscordUserConfig).where(DiscordUserConfig.user_id == user_id)
            )
            return result.scalar_one_or_none()
    
    # ========== Update Check Repository ==========
    
    async def save_update_check(self, update_data: Dict[str, Any]) -> UpdateCheck:
        """Save update check result"""
        async with await self.get_session() as session:
            # Get or create
            result = await session.execute(select(UpdateCheck).order_by(UpdateCheck.id.desc()))
            check = result.scalar_one_or_none()
            
            if check:
                check.current_version = update_data.get('current_version', check.current_version)
                check.latest_version = update_data.get('latest_version')
                check.update_available = update_data.get('update_available', False)
                check.release_notes = update_data.get('release_notes')
                check.release_url = update_data.get('release_url')
                check.last_checked_at = datetime.utcnow()
                check.last_check_success = update_data.get('success', True)
                check.last_check_error = update_data.get('error')
            else:
                check = UpdateCheck(**update_data)
                session.add(check)
            
            await session.commit()
            await session.refresh(check)
            return check
    
    async def get_last_update_check(self) -> Optional[UpdateCheck]:
        """Get last update check result"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(UpdateCheck).order_by(UpdateCheck.id.desc())
            )
            return result.scalar_one_or_none()
    
    # ========== System Events Repository ==========
    
    async def log_system_event(
        self,
        event_type: str,
        message: str,
        source: str = 'system',
        severity: str = 'info',
        details: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> SystemEvent:
        """Log a system event"""
        async with await self.get_session() as session:
            event = SystemEvent(
                event_type=event_type,
                message=message,
                source=source,
                severity=severity,
                details=details,
                user_id=user_id
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event
    
    async def get_recent_events(self, limit: int = 50) -> List[SystemEvent]:
        """Get recent system events"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(SystemEvent)
                .order_by(SystemEvent.timestamp.desc())
                .limit(limit)
            )
            return list(result.scalars().all())


# Global database manager instance
db_manager = DatabaseManager()


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    return db_manager
