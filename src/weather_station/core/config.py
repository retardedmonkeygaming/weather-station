from pydantic_settings import BaseSettings, SettingsConfigDict

class WeatherSettings(BaseSettings):
    latitude: str = "29.325390"
    longitude: str = "48.019562"
    unit: str = "C"
    buzzer_mode: str = "ALL"
    api_rate: int = 10
    log_rate: int = 15
    db_file: str = "weather_history.db"
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    dht_temp_offset: float = 0.0
    
    # ADD THIS LINE
    discord_token: str = "" 
    # Add this line to your WeatherSettings class
    lyrics_db: str = "lyrics.db"
    model_config = SettingsConfigDict(env_prefix="WEATHER_", env_file=".env", extra="ignore")

settings = WeatherSettings()