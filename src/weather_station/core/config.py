from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List
import os
from weather_station import PROJECT_NAME, __version__


class ProjectSettings(BaseSettings):
    """Project metadata settings."""
    name: str = Field(default=PROJECT_NAME, description="Project name")
    version: str = Field(default=__version__, description="Project version")
    tagline: str = Field(default="Professional Weather Monitoring", description="Project tagline")
    primary_color: str = Field(default="#0288d1", description="Primary brand color")
    lcd_color: str = Field(default="#4CAF50", description="LCD green color")


class WeatherSettings(BaseSettings):
    """Central configuration for SkyCast Weather Station.
    
    All settings can be overridden via environment variables with WEATHER_ prefix.
    Example: WEATHER_LATITUDE=29.325390
    """
    
    # ==========================================================================
    # Project Metadata (read-only)
    # ==========================================================================
    project: ProjectSettings = Field(default_factory=ProjectSettings)
    
    # ==========================================================================
    # Location & Geography
    # ==========================================================================
    latitude: str = Field(default="29.325390", description="Latitude for weather API queries")
    longitude: str = Field(default="48.019562", description="Longitude for weather API queries")
    timezone: str = Field(default="UTC", description="Timezone for display")
    
    # ==========================================================================
    # Display & Units
    # ==========================================================================
    unit: str = Field(default="C", description="Temperature unit: C or F")
    language: str = Field(default="en", description="Display language code")
    theme: str = Field(default="auto", description="UI theme: light, dark, auto")
    
    # ==========================================================================
    # Hardware Configuration
    # ==========================================================================
    buzzer_mode: str = Field(default="ALL", description="Buzzer mode: ALL, ERR, MUTE")
    dht_temp_offset: float = Field(default=0.0, description="Temperature calibration offset")
    dht_humid_offset: float = Field(default=0.0, description="Humidity calibration offset")
    idle_timeout: int = Field(default=300, description="Seconds before LCD dims")
    
    # ==========================================================================
    # Timing & Intervals
    # ==========================================================================
    api_rate: int = Field(default=10, ge=1, le=120, description="Minutes between API fetches")
    log_rate: int = Field(default=15, ge=1, le=1440, description="Minutes between DB logs")
    
    # ==========================================================================
    # Web Server
    # ==========================================================================
    web_host: str = Field(default="0.0.0.0", description="Web server bind address")
    web_port: int = Field(default=8000, ge=1, le=65535, description="Web server port")
    
    # ==========================================================================
    # Database
    # ==========================================================================
    db_file: str = Field(default="weather_history.db", description="SQLite database filename")
    
    # ==========================================================================
    # Discord Bot
    # ==========================================================================
    discord_token: Optional[str] = Field(default=None, description="Discord bot token")
    discord_channel_id: Optional[int] = Field(default=None, description="Default Discord channel ID")
    discord_owner_ids: List[int] = Field(default_factory=list, description="List of Discord user IDs with owner permissions")
    
    # ==========================================================================
    # Alerts & Notifications
    # ==========================================================================
    alert_enabled: bool = Field(default=False, description="Enable scheduled alerts")
    alert_hour: int = Field(default=17, ge=0, le=23, description="Alert hour (24h format)")
    alert_minute: int = Field(default=0, ge=0, le=59, description="Alert minute")
    quiet_hours_start: int = Field(default=22, ge=0, le=23, description="Quiet hours start hour")
    quiet_hours_end: int = Field(default=7, ge=0, le=23, description="Quiet hours end hour")
    
    # ==========================================================================
    # Temperature/Humidity Alert Thresholds
    # ==========================================================================
    temp_high_alert: Optional[float] = Field(default=None, description="High temperature alert threshold")
    temp_low_alert: Optional[float] = Field(default=None, description="Low temperature alert threshold")
    humid_high_alert: Optional[float] = Field(default=None, description="High humidity alert threshold")
    humid_low_alert: Optional[float] = Field(default=None, description="Low humidity alert threshold")
    
    # ==========================================================================
    # Update Checking
    # ==========================================================================
    check_updates: bool = Field(default=True, description="Check for GitHub updates")
    github_repo: str = Field(default="yourusername/weather-station", description="GitHub repository for update checks")
    
    # ==========================================================================
    # Validation
    # ==========================================================================
    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if v not in ("C", "F"):
            raise ValueError("unit must be 'C' or 'F'")
        return v
    
    @field_validator("buzzer_mode")
    @classmethod
    def validate_buzzer_mode(cls, v: str) -> str:
        if v not in ("ALL", "ERR", "MUTE"):
            raise ValueError("buzzer_mode must be 'ALL', 'ERR', or 'MUTE'")
        return v
    
    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        if v not in ("light", "dark", "auto"):
            raise ValueError("theme must be 'light', 'dark', or 'auto'")
        return v

    model_config = SettingsConfigDict(
        env_prefix="WEATHER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global settings instance
settings = WeatherSettings()