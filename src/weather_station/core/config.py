from pydantic_settings import BaseSettings, SettingsConfigDict

class WeatherSettings(BaseSettings):
    # Location
    latitude: str = "29.325390"
    longitude: str = "48.019562"
    
    # Unit Settings
    unit: str = "C"
    buzzer_mode: str = "ALL"
    
    # Intervals (minutes)
    api_rate: int = 10
    log_rate: int = 15
    
    # Database
    db_file: str = "weather_history.db"

    # --- ADD THESE TWO LINES ---
    web_host: str = "0.0.0.0"
    web_port: int = 8000

    # Sensor Thresholds (Your original script had these)
    temp_high_threshold: float = 32.0
    temp_low_threshold: float = 10.0
    dht_temp_offset: float = 0.0

    model_config = SettingsConfigDict(
        env_prefix="WEATHER_",
        env_file=".env",
        extra="ignore"
    )

settings = WeatherSettings()