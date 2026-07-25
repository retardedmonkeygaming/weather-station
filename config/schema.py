"""Configuration models and loading."""
import os
from pydantic import BaseModel
import yaml


class HardwareConfig(BaseModel):
    dht_pin: int = 4
    touch_pin: int = 27
    buzzer_pin: int = 2
    lcd_rs: int = 22
    lcd_en: int = 17
    lcd_d4: int = 25
    lcd_d5: int = 24
    lcd_d6: int = 23
    lcd_d7: int = 18


class AppConfig(BaseModel):
    environment: str = "production"  # 'production' or 'mock'
    db_file: str = "weather_history.db"
    latitude: float = 29.3759
    longitude: float = 47.9774
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    hardware: HardwareConfig = HardwareConfig()


def load_config(config_path: str = "config/default.yaml") -> AppConfig:
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
            return AppConfig(**data)
    return AppConfig()