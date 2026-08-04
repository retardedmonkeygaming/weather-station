from pydantic_settings import BaseSettings, SettingsConfigDict

class WeatherSettings(BaseSettings):
    """
    Handles all application settings. 
    Can be overridden by environment variables (e.g., WEATHER_UNIT=F).
    """
    # Location
    latitude: str = "29.325390"
    longitude: str = "48.019562"
    
    # Unit Settings
    unit: str = "C"
    buzzer_mode: str = "ALL"  # ALL, ERR, MUTE
    
    # Intervals (minutes)
    api_rate: int = 10
    log_rate: int = 15
    
    # Database
    db_file: str = "weather_history.db"

    model_config = SettingsConfigDict(
        env_prefix="WEATHER_",
        env_file=".env",
        extra="ignore"
    )

settings = WeatherSettings()