from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class AppState:
    # Environment Data
    indoor_temp: Optional[float] = None
    indoor_temp_raw: Optional[float] = None
    indoor_humid: Optional[float] = None
    outdoor_temp: str = "N/A"
    outdoor_humid: str = "N/A"
    outdoor_min: str = "N/A"
    outdoor_max: str = "N/A"
    
    # AQI & UV Data
    aqi_val: str = "N/A"
    aqi_status: str = "N/A"
    pm2_5: str = "N/A"
    pm10: str = "N/A"
    uv_index: str = "N/A"
    uv_max: str = "N/A"
    
    # Icons & Text
    weather_icon: str = "\x05"
    weather_text: str = "Clear"
    temp_trend_symbol: str = "->"
    
    # Navigation
    current_page: int = 1
    total_pages: int = 6
    in_settings_mode: bool = False
    settings_index: int = 1
    
    # Flags
    dht_error: bool = False
    wifi_error: bool = False
    last_dht_error: bool = False
    last_wifi_error: bool = False
    
    # High-Priority System Messages (Reboot/Shutdown)
    system_message: Optional[tuple] = None # Stores (Line1, Line2)
    
    # Web UI Communication (Live Preview)
    last_line1: str = ""
    last_line2: str = ""
    
    # Designer overrides
    custom_pages: Dict[int, str] = field(default_factory=dict)

state = AppState()