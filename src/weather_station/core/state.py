"""
Central application state - single source of truth
Replaces dozens of globals with a typed, observable store
"""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SystemStatus(Enum):
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class SensorData:
    """Current sensor readings"""
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    aqi: Optional[int] = None
    aqi_status: str = "OK"
    feels_like: Optional[float] = None
    dew_point: Optional[float] = None
    
    # Timestamps
    last_updated: Optional[datetime] = None
    last_api_fetch: Optional[datetime] = None
    
    # Quality indicators
    sensor_error: bool = False
    api_error: bool = False
    consecutive_failures: int = 0


@dataclass
class DisplayState:
    """Display-related state"""
    current_page: int = 0
    total_pages: int = 6
    in_settings: bool = False
    settings_index: int = 0
    backlight_on: bool = True
    brightness: int = 100  # 0-100
    auto_dim_enabled: bool = True
    last_interaction: Optional[datetime] = None
    boot_splash_shown: bool = False


@dataclass
class AlertState:
    """Alert-related state"""
    alerts_active: List[Dict[str, Any]] = field(default_factory=list)
    buzzer_active: bool = False
    quiet_hours_active: bool = False
    last_alert_time: Optional[datetime] = None


@dataclass
class SystemInfo:
    """System information"""
    uptime_seconds: float = 0.0
    start_time: datetime = field(default_factory=datetime.utcnow)
    status: SystemStatus = SystemStatus.STARTING
    version: str = "3.0.0"
    disk_free_mb: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    cpu_usage_percent: Optional[float] = None


@dataclass
class DiscordState:
    """Discord bot state"""
    connected: bool = False
    guild_count: int = 0
    user_count: int = 0
    last_message_time: Optional[datetime] = None


@dataclass
class AppState:
    """
    Central application state - single source of truth.
    All components read from and write to this shared state.
    Thread-safe with asyncio lock.
    """
    
    # Sensor data
    sensor: SensorData = field(default_factory=SensorData)
    
    # Display state
    display: DisplayState = field(default_factory=DisplayState)
    
    # Alerts
    alerts: AlertState = field(default_factory=AlertState)
    
    # System info
    system: SystemInfo = field(default_factory=SystemInfo)
    
    # Discord state
    discord: DiscordState = field(default_factory=DiscordState)
    
    # Settings cache (loaded from DB)
    settings_cache: Dict[str, Any] = field(default_factory=dict)
    
    # Message of the day (configurable)
    message_of_the_day: str = ""
    
    # Station ID (for multi-station readiness)
    station_id: str = "default"
    
    # Lock for thread-safe access
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    async def update_sensor(self, **kwargs) -> None:
        """Thread-safe sensor data update"""
        async with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.sensor, key):
                    setattr(self.sensor, key, value)
            if 'temperature' in kwargs or 'humidity' in kwargs:
                self.sensor.last_updated = datetime.utcnow()
    
    async def update_display(self, **kwargs) -> None:
        """Thread-safe display state update"""
        async with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.display, key):
                    setattr(self.display, key, value)
            self.display.last_interaction = datetime.utcnow()
    
    async def add_alert(self, alert_type: str, message: str, severity: str = "warning") -> None:
        """Add an active alert"""
        async with self._lock:
            alert = {
                'type': alert_type,
                'message': message,
                'severity': severity,
                'timestamp': datetime.utcnow()
            }
            self.alerts.alerts_active.append(alert)
            self.alerts.last_alert_time = datetime.utcnow()
    
    async def clear_alerts(self, alert_type: Optional[str] = None) -> None:
        """Clear alerts, optionally by type"""
        async with self._lock:
            if alert_type:
                self.alerts.alerts_active = [
                    a for a in self.alerts.alerts_active 
                    if a['type'] != alert_type
                ]
            else:
                self.alerts.alerts_active.clear()
    
    async def get_state_dict(self) -> Dict[str, Any]:
        """Get complete state as dictionary (for API/WebSocket)"""
        async with self._lock:
            return {
                'sensor': {
                    'temperature': self.sensor.temperature,
                    'humidity': self.sensor.humidity,
                    'pressure': self.sensor.pressure,
                    'aqi': self.sensor.aqi,
                    'aqi_status': self.sensor.aqi_status,
                    'feels_like': self.sensor.feels_like,
                    'last_updated': self.sensor.last_updated.isoformat() if self.sensor.last_updated else None,
                    'last_api_fetch': self.sensor.last_api_fetch.isoformat() if self.sensor.last_api_fetch else None,
                    'sensor_error': self.sensor.sensor_error,
                    'api_error': self.sensor.api_error,
                },
                'display': {
                    'current_page': self.display.current_page,
                    'in_settings': self.display.in_settings,
                    'backlight_on': self.display.backlight_on,
                },
                'alerts': {
                    'active_count': len(self.alerts.alerts_active),
                    'buzzer_active': self.alerts.buzzer_active,
                    'quiet_hours': self.alerts.quiet_hours_active,
                },
                'system': {
                    'uptime_seconds': self.system.uptime_seconds,
                    'status': self.system.status.value,
                    'version': self.system.version,
                    'disk_free_mb': self.system.disk_free_mb,
                },
                'discord': {
                    'connected': self.discord.connected,
                    'guild_count': self.discord.guild_count,
                },
                'station_id': self.station_id,
                'message_of_the_day': self.message_of_the_day,
            }


# Global app state instance
app_state = AppState()
