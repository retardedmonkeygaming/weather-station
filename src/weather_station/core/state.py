from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class AppState:
    # Environment Data
    indoor_temp: Optional[float] = None
    indoor_humid: Optional[float] = None
    outdoor_temp: str = "N/A"
    outdoor_humid: str = "N/A"
    outdoor_max: str = "N/A"
    outdoor_min: str = "N/A"
    aqi_val: str = "N/A"
    aqi_status: str = "N/A"
    
    # LCD Navigation
    current_page: int = 1
    total_pages: int = 6
    in_settings_mode: bool = False
    settings_index: int = 1
    total_settings: int = 10
    
    # Error Flags
    dht_error: bool = False
    wifi_error: bool = False
    
    # Symbols & Icons
    temp_trend_symbol: str = "->"
    clock_icon: str = "\x00"  # Hourglass
    
    # Web UI Designer
    custom_pages: Dict[int, str] = field(default_factory=dict)

state = AppState()