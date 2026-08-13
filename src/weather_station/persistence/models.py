"""
SQLAlchemy ORM models for all database tables
Schema versioning and migration support
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()


class Setting(Base):
    """
    Application settings with provenance tracking.
    Every setting stores who changed it and when.
    """
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), default='string')  # string, int, float, bool, json
    
    # Provenance tracking
    last_changed_by = Column(String(50), default='system')  # hardware, web, discord, system
    last_changed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    changed_by_user_id = Column(String(100), nullable=True)  # Discord user ID if applicable
    
    # Metadata
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=False)  # System settings can't be changed by users
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_settings_key', 'key'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'key': self.key,
            'value': self.get_typed_value(),
            'value_type': self.value_type,
            'last_changed_by': self.last_changed_by,
            'last_changed_at': self.last_changed_at.isoformat() if self.last_changed_at else None,
            'changed_by_user_id': self.changed_by_user_id,
            'description': self.description,
            'is_system': self.is_system,
        }
    
    def get_typed_value(self):
        """Get value with proper type conversion"""
        if self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        return self.value


class SensorLog(Base):
    """
    Historical sensor readings.
    Automatic retention policy removes old entries.
    """
    __tablename__ = 'sensor_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    station_id = Column(String(50), default='default', index=True)
    
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    pressure = Column(Float, nullable=True)
    aqi = Column(Integer, nullable=True)
    aqi_status = Column(String(20), nullable=True)
    feels_like = Column(Float, nullable=True)
    
    source = Column(String(20), default='api')  # api, sensor, mock
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_sensor_logs_timestamp', 'timestamp'),
        Index('idx_sensor_logs_station', 'station_id'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'station_id': self.station_id,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'pressure': self.pressure,
            'aqi': self.aqi,
            'aqi_status': self.aqi_status,
            'feels_like': self.feels_like,
            'source': self.source,
        }


class AlertLog(Base):
    """
    Alert history for auditing and analysis.
    """
    __tablename__ = 'alert_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    station_id = Column(String(50), default='default')
    
    alert_type = Column(String(50), nullable=False)  # temp_high, temp_low, humidity_high, aqi_unhealthy, etc.
    severity = Column(String(20), default='warning')  # info, warning, critical
    message = Column(Text, nullable=False)
    
    value = Column(Float, nullable=True)  # The value that triggered the alert
    threshold = Column(Float, nullable=True)  # The threshold that was exceeded
    
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_alert_logs_timestamp', 'timestamp'),
        Index('idx_alert_logs_type', 'alert_type'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved,
        }


class DiscordServerConfig(Base):
    """
    Per-server Discord configuration.
    Stores channel IDs, roles, and server-specific settings.
    """
    __tablename__ = 'discord_server_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(String(50), unique=True, nullable=False, index=True)  # Discord server ID
    guild_name = Column(String(100), nullable=True)
    
    # Configuration
    alerts_channel_id = Column(String(50), nullable=True)  # Channel for alerts
    briefing_channel_id = Column(String(50), nullable=True)  # Channel for daily briefings
    allowed_role_ids = Column(JSON, default=list)  # Roles allowed to use control commands
    
    # Features
    natural_language_enabled = Column(Boolean, default=True)
    briefing_enabled = Column(Boolean, default=False)
    briefing_time = Column(String(10), default='08:00')  # HH:MM format
    quiet_hours_start = Column(Integer, default=22)  # 0-23
    quiet_hours_end = Column(Integer, default=7)  # 0-23
    
    # State
    setup_completed = Column(Boolean, default=False)
    setup_completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'guild_id': self.guild_id,
            'guild_name': self.guild_name,
            'alerts_channel_id': self.alerts_channel_id,
            'briefing_channel_id': self.briefing_channel_id,
            'allowed_role_ids': self.allowed_role_ids or [],
            'natural_language_enabled': self.natural_language_enabled,
            'briefing_enabled': self.briefing_enabled,
            'briefing_time': self.briefing_time,
            'quiet_hours_start': self.quiet_hours_start,
            'quiet_hours_end': self.quiet_hours_end,
            'setup_completed': self.setup_completed,
        }


class DiscordUserConfig(Base):
    """
    Per-user Discord configuration.
    Stores personal preferences and thresholds.
    """
    __tablename__ = 'discord_user_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)  # Discord user ID
    username = Column(String(100), nullable=True)
    
    # Preferences
    preferred_units = Column(String(10), default='metric')  # metric or imperial
    dm_alerts_enabled = Column(Boolean, default=False)
    dm_briefing_enabled = Column(Boolean, default=False)
    
    # Personal thresholds (override global)
    personal_temp_high = Column(Float, nullable=True)
    personal_temp_low = Column(Float, nullable=True)
    personal_humidity_high = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'preferred_units': self.preferred_units,
            'dm_alerts_enabled': self.dm_alerts_enabled,
            'dm_briefing_enabled': self.dm_briefing_enabled,
            'personal_temp_high': self.personal_temp_high,
            'personal_temp_low': self.personal_temp_low,
            'personal_humidity_high': self.personal_humidity_high,
        }


class UpdateCheck(Base):
    """
    GitHub update check results.
    Stores last check time and available updates.
    """
    __tablename__ = 'update_checks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    current_version = Column(String(20), nullable=False)
    latest_version = Column(String(20), nullable=True)
    update_available = Column(Boolean, default=False)
    
    release_notes = Column(Text, nullable=True)
    release_url = Column(String(255), nullable=True)
    checksum = Column(String(64), nullable=True)  # SHA256
    
    last_checked_at = Column(DateTime, default=datetime.utcnow)
    last_check_success = Column(Boolean, default=True)
    last_check_error = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'current_version': self.current_version,
            'latest_version': self.latest_version,
            'update_available': self.update_available,
            'release_notes': self.release_notes,
            'release_url': self.release_url,
            'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None,
            'last_check_success': self.last_check_success,
        }


class SystemEvent(Base):
    """
    System events for auditing and debugging.
    """
    __tablename__ = 'system_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    event_type = Column(String(50), nullable=False)  # startup, shutdown, reboot, factory_reset, config_change, etc.
    source = Column(String(50), default='system')  # system, hardware, web, discord
    severity = Column(String(20), default='info')  # debug, info, warning, error, critical
    
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)  # Additional structured data
    
    user_id = Column(String(100), nullable=True)  # If triggered by a user
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_system_events_timestamp', 'timestamp'),
        Index('idx_system_events_type', 'event_type'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'event_type': self.event_type,
            'source': self.source,
            'severity': self.severity,
            'message': self.message,
            'details': self.details,
            'user_id': self.user_id,
        }
