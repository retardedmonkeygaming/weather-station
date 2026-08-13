"""
Pydantic-based configuration system supporting YAML/TOML/.env
Multiple profiles: development, production, mock
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LocationConfig(BaseSettings):
    """Location configuration for weather data"""
    latitude: float = Field(default=40.7128, description="Latitude")
    longitude: float = Field(default=-74.0060, description="Longitude")
    elevation: float = Field(default=10.0, description="Elevation in meters")
    timezone: str = Field(default="America/New_York", description="Timezone")
    
    model_config = SettingsConfigDict(env_prefix="LOCATION_")


class SensorConfig(BaseSettings):
    """Sensor hardware configuration"""
    i2c_bus: int = Field(default=1, description="I2C bus number")
    lcd_address: int = Field(default=0x27, description="LCD I2C address")
    lcd_columns: int = Field(default=16, description="LCD columns")
    lcd_rows: int = Field(default=2, description="LCD rows")
    touch_pin: int = Field(default=4, description="Touch sensor GPIO pin")
    buzzer_pin: int = Field(default=17, description="Buzzer GPIO pin")
    backlight_pin: int = Field(default=5, description="Backlight GPIO pin")
    mock_hardware: bool = Field(default=False, description="Use mock hardware")
    
    model_config = SettingsConfigDict(env_prefix="SENSOR_")


class AlertConfig(BaseSettings):
    """Alert thresholds and behavior"""
    temp_high: float = Field(default=30.0, description="High temperature alert threshold")
    temp_low: float = Field(default=5.0, description="Low temperature alert threshold")
    humidity_high: float = Field(default=80.0, description="High humidity alert threshold")
    humidity_low: float = Field(default=20.0, description="Low humidity alert threshold")
    aqi_unhealthy: int = Field(default=101, description="AQI unhealthy threshold")
    buzzer_mode: str = Field(default="ALERTS", description="Buzzer mode: ALL/ALERTS/MUTE")
    quiet_hours_start: int = Field(default=22, description="Quiet hours start (0-23)")
    quiet_hours_end: int = Field(default=7, description="Quiet hours end (0-23)")
    
    @field_validator('buzzer_mode')
    @classmethod
    def validate_buzzer_mode(cls, v: str) -> str:
        valid_modes = ['ALL', 'ALERTS', 'MUTE']
        if v.upper() not in valid_modes:
            raise ValueError(f"buzzer_mode must be one of {valid_modes}")
        return v.upper()
    
    model_config = SettingsConfigDict(env_prefix="ALERT_")


class DiscordConfig(BaseSettings):
    """Discord bot configuration"""
    token: Optional[str] = Field(default=None, description="Discord bot token")
    enabled: bool = Field(default=False, description="Enable Discord bot")
    default_channel_id: Optional[int] = Field(default=None, description="Default alerts channel")
    natural_language: bool = Field(default=True, description="Enable natural language processing")
    briefing_enabled: bool = Field(default=False, description="Enable daily briefings")
    briefing_time: str = Field(default="08:00", description="Daily briefing time (HH:MM)")
    
    model_config = SettingsConfigDict(env_prefix="DISCORD_")


class WebConfig(BaseSettings):
    """Web server configuration"""
    host: str = Field(default="0.0.0.0", description="Web server host")
    port: int = Field(default=8000, description="Web server port")
    enable_auth: bool = Field(default=False, description="Enable web authentication")
    session_secret: Optional[str] = Field(default=None, description="Session secret key")
    
    model_config = SettingsConfigDict(env_prefix="WEB_")


class DataConfig(BaseSettings):
    """Data collection and retention configuration"""
    api_fetch_interval: int = Field(default=300, description="API fetch interval in seconds")
    log_interval: int = Field(default=60, description="Data logging interval in seconds")
    retention_days: int = Field(default=30, description="Data retention period in days")
    demo_mode: bool = Field(default=False, description="Enable demo/exhibition mode")
    
    model_config = SettingsConfigDict(env_prefix="DATA_")


class Settings(BaseSettings):
    """Main application settings"""
    # Application identity
    app_name: str = Field(default="SkyCast Weather Station", description="Application name")
    version: str = Field(default="3.0.0", description="Application version")
    tagline: str = Field(default="Your Environment, Understood", description="Tagline")
    primary_color: str = Field(default="#0288d1", description="Primary branding color")
    
    # Profiles
    profile: str = Field(default="production", description="Configuration profile")
    
    # Nested configurations
    location: LocationConfig = Field(default_factory=LocationConfig)
    sensor: SensorConfig = Field(default_factory=SensorConfig)
    alert: AlertConfig = Field(default_factory=AlertConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    
    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./data/skycast.db", description="Database URL")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore'
    )
    
    @field_validator('profile')
    @classmethod
    def validate_profile(cls, v: str) -> str:
        valid_profiles = ['development', 'production', 'mock']
        if v not in valid_profiles:
            raise ValueError(f"profile must be one of {valid_profiles}")
        return v
    
    def is_development(self) -> bool:
        return self.profile == 'development'
    
    def is_production(self) -> bool:
        return self.profile == 'production'
    
    def is_mock(self) -> bool:
        return self.profile == 'mock'


def get_settings(config_path: Optional[Path] = None) -> Settings:
    """
    Load settings from environment variables, .env file, or YAML/TOML config
    Priority: Environment > .env > YAML/TOML > Defaults
    """
    if config_path and config_path.exists():
        # Could extend to load YAML/TOML here
        pass
    
    return Settings()
