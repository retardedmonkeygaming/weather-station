from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

@dataclass
class AppState:
    # --- Environment Data ---
    indoor_temp: Optional[float] = None
    indoor_temp_raw: Optional[float] = None
    indoor_humid: Optional[float] = None
    outdoor_temp: str = "N/A"
    outdoor_humid: str = "N/A"
    outdoor_min: str = "N/A"
    outdoor_max: str = "N/A"
    
    # --- AQI & UV Data ---
    aqi_val: str = "N/A"
    aqi_status: str = "N/A"
    pm2_5: str = "N/A"
    pm10: str = "N/A"
    uv_index: str = "N/A"
    uv_max: str = "N/A"
    
    # --- Icons & Text ---
    weather_icon: str = "\x05"
    weather_text: str = "Clear"
    temp_trend_symbol: str = "->"
    
    # --- Navigation & System ---
    current_page: int = 1
    total_pages: int = 6
    in_settings_mode: bool = False
    settings_index: int = 1
    
    # --- Flags ---
    dht_error: bool = False
    wifi_error: bool = False
    last_dht_error: bool = False
    last_wifi_error: bool = False
    
    # --- LYRICPULSE STATE ---
    is_lyric_active: bool = False
    lyric_state: str = "IDLE"  # IDLE, MENU, PLAYING
    current_song_title: str = ""
    current_lyric_line1: str = ""
    current_lyric_line2: str = ""
    songs_list: List[Dict[str, Any]] = field(default_factory=list)
    selected_song_index: int = 0
    
    # --- UI & High-Priority Overrides ---
    system_message: Optional[tuple] = None # Stores (Line1, Line2)
    last_line1: str = ""
    last_line2: str = ""
    custom_pages: Dict[int, str] = field(default_factory=dict)

state = AppState()