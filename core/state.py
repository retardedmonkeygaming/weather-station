"""Central application state store."""
import asyncio
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AppStateModel(BaseModel):
    # Indoor Readings
    indoor_temp: Optional[float] = None
    indoor_humid: Optional[float] = None
    
    # Outdoor Readings
    outdoor_temp: Optional[float] = None
    outdoor_humid: Optional[float] = None
    outdoor_min: Optional[float] = None
    outdoor_max: Optional[float] = None
    uv_current: Optional[float] = None
    uv_max: Optional[float] = None
    
    # Air Quality
    aqi_val: str = "N/A"
    aqi_status: str = "Unknown"
    pm2_5_val: str = "N/A"
    pm10_val: str = "N/A"
    
    # System Status
    dht_error: bool = False
    wifi_error: bool = False
    pi_cpu_temp: str = "N/A"
    pi_cpu_usage: str = "N/A"
    pi_ram_usage: str = "N/A"
    
    # Active LCD State
    last_lcd_rendered_text: List[str] = Field(default_factory=lambda: ["Initializing...", "Please wait"])
    current_page: int = 1
    total_pages: int = 5
    in_settings_mode: bool = False
    settings_page_index: int = 0
    total_settings_count: int = 7
    
    # Settings
    temp_unit: str = "C"
    buzzer_mode: str = "ALL"
    backlight_enabled: bool = True
    auto_scroll_speed: int = 3
    alarm_time: str = "07:00"
    alarm_enabled: bool = False
    log_interval: int = 300
    api_fetch_interval: int = 600
    night_mode: bool = False
    
    # Offsets
    temp_offset: float = 0.0
    humid_offset: float = 0.0


class AppState:
    def __init__(self):
        self._data = AppStateModel()
        self._lock = asyncio.Lock()
        self.custom_lcd_pages: Dict[int, str] = {}

    async def update(self, **kwargs):
        async with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._data, key):
                    setattr(self._data, key, value)

    async def get_snapshot(self) -> AppStateModel:
        async with self._lock:
            return self._data.model_copy()

    def get_snapshot_sync(self) -> AppStateModel:
        return self._data.model_copy()


state = AppState()