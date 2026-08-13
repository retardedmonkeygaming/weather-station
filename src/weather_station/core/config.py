from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class WeatherSettings(BaseSettings):
    # Location
    latitude: str = "29.325390"
    longitude: str = "48.019562"
    
    # Display & Units
    unit: str = "C"
    language: str = "en"
    
    # Hardware
    buzzer_mode: str = "ALL"  # ALL, ERR, MUTE
    dht_temp_offset: float = 0.0
    
    # Timing
    api_rate: int = 10  # minutes
    log_rate: int = 15  # minutes
    idle_timeout: int = 300  # seconds before LCD dim
    
    # Web Server
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    
    # Database
    db_file: str = "weather_history.db"
    
    # Discord
    discord_token: Optional[str] = None
    discord_channel_id: Optional[int] = None
    
    # Alerts
    alert_enabled: bool = False
    alert_hour: int = 17
    alert_minute: int = 0
    
    # UI Preferences
    theme: str = "auto"  # light, dark, auto
    
    model_config = SettingsConfigDict(env_prefix="WEATHER_", env_file=".env", extra="ignore")

settings = WeatherSettings()