"""
Core Application State Management
Holds all live sensor data, system status, and runtime configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class SystemStatus(Enum):
    BOOTING = "booting"
    RUNNING = "running"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class SensorData:
    """Live sensor readings"""
    indoor_temp_raw: Optional[float] = None
    indoor_temp: Optional[float] = None
    indoor_humidity: Optional[float] = None
    outdoor_temp: Optional[float] = None
    outdoor_humidity: Optional[float] = None
    outdoor_temp_min: Optional[float] = None
    outdoor_temp_max: Optional[float] = None
    uv_index: Optional[float] = None
    uv_index_max: Optional[float] = None
    weather_code: int = 0
    aqi: Optional[int] = None
    aqi_status: str = "N/A"
    pm2_5: Optional[float] = None
    pm10: Optional[float] = None
    last_updated: Optional[datetime] = None


@dataclass
class SystemInfo:
    """Raspberry Pi system metrics"""
    cpu_temp: Optional[float] = None
    cpu_usage: float = 0.0
    ram_usage: float = 0.0
    uptime_seconds: float = 0.0


@dataclass
class MoonData:
    """Moon phase information"""
    phase_name: str = "Unknown"
    short_name: str = "Unknown"
    illumination: int = 0
    age_days: float = 0.0


@dataclass
class AlertState:
    """Active alert information"""
    is_active: bool = False
    alert_type: str = ""  # "temperature_high", "temperature_low", "alarm"
    message: str = ""
    triggered_at: Optional[datetime] = None


@dataclass
class HardwareStatus:
    """Hardware component health"""
    dht_error: bool = False
    wifi_error: bool = False
    buzzer_muted: bool = False
    screen_on: bool = True


@dataclass
class DisplayState:
    """LCD display state"""
    current_page: int = 1
    total_pages: int = 6
    in_settings_mode: bool = False
    settings_index: int = 1
    auto_scroll_enabled: bool = False
    auto_scroll_interval: int = 0
    custom_pages: Dict[int, str] = field(default_factory=dict)
    last_rendered_lines: List[str] = field(default_factory=lambda: ["", ""])


@dataclass
class AlarmConfig:
    """Alarm configuration"""
    enabled: bool = False
    hour: int = 17
    minute: int = 0
    ringing: bool = False
    dismissed_today: bool = False


@dataclass
class LocationConfig:
    """Geographic location"""
    latitude: str = "29.325390"
    longitude: str = "48.019562"


class AppState:
    """
    Central application state container.
    All components read from and write to this single source of truth.
    """
    
    def __init__(self):
        # Core state
        self.status = SystemStatus.BOOTING
        self.start_time = datetime.now()
        
        # Data containers
        self.sensors = SensorData()
        self.system = SystemInfo()
        self.moon = MoonData()
        self.alert = AlertState()
        self.hardware = HardwareStatus()
        self.display = DisplayState()
        self.alarm = AlarmConfig()
        self.location = LocationConfig()
        
        # Calibration & thresholds
        self.temp_offset: float = 0.0
        self.temp_high_threshold: float = 32.0
        self.temp_low_threshold: float = 10.0
        
        # Temp history for trend calculation
        self.temp_history: List[tuple] = []  # (timestamp, temperature)
        
        # Version info
        self.version = "2.0.0"
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def is_night_time(self) -> bool:
        """Check if current time is within night hours (23:00 - 07:00)"""
        hour = datetime.now().hour
        return hour >= 23 or hour < 7
    
    def get_api_urls(self) -> tuple[str, str]:
        """Build Open-Meteo API URLs based on location"""
        base = f"https://api.open-meteo.com/v1/forecast?latitude={self.location.latitude}&longitude={self.location.longitude}"
        weather_url = f"{base}&current=temperature_2m,relative_humidity_2m,weather_code,uv_index&daily=temperature_2m_max,temperature_2m_min,uv_index_max&timezone=auto"
        aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={self.location.latitude}&longitude={self.location.longitude}&current=us_aqi,pm10,pm2_5"
        return weather_url, aqi_url
    
    def reset_to_defaults(self):
        """Reset runtime state to defaults (used during factory reset)"""
        self.sensors = SensorData()
        self.alert = AlertState()
        self.hardware = HardwareStatus()
        self.display = DisplayState()
        self.alarm = AlarmConfig()
        self.location = LocationConfig()
        self.temp_offset = 0.0
        self.temp_history.clear()
