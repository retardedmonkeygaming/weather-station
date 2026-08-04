from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class AppState:
    # Sensor Data
    indoor_temp: Optional[float] = None
    indoor_humid: Optional[float] = None
    outdoor_temp: str = "N/A"
    outdoor_humid: str = "N/A"
    
    # Status Flags
    dht_error: bool = False
    wifi_error: bool = False
    alarm_ringing: bool = False
    
    # LCD State
    current_page: int = 1
    total_pages: int = 6
    page_changed: bool = True
    
    # History for trends
    temp_history: List[float] = field(default_factory=list)
    
    # Web UI Designer
    custom_pages: Dict[int, str] = field(default_factory=dict)

    current_page: int = 1
    total_pages: int = 6  # ENSURE THIS IS 6
    aqi_val: str = "N/A"
    
# Global shared state instance
state = AppState()