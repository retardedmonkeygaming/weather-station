"""
LCD Widget Definitions
All widgets for the 16x2 display with proper formatting

Pages:
0. Clock + Date (permanent page 1)
1. Indoor Climate (temp + humidity + comfort)
2. Outdoor Weather (temp + feels like + conditions)
3. Air Quality (AQI status - non-truncating words)
4. System Info (uptime, API age, disk space)
5. Settings Menu (10 items)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import math


class BaseWidget(ABC):
    """Base class for all LCD widgets"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def render(self, state: Any, lcd_interface) -> None:
        """Render the widget on the LCD"""
        pass


class ClockWidget(BaseWidget):
    """
    Page 0: Clock + Date with animated colon and alarm indicator
    Format:
    Row 0: HH:MM:SS [alarm_icon]
    Row 1: Mon DD, YYYY
    """
    
    def __init__(self):
        super().__init__("Clock")
        self._last_second = -1
        self._colon_visible = True
    
    async def render(self, state: Any, lcd_interface) -> None:
        now = datetime.utcnow()
        
        # Animate colon every second
        if now.second != self._last_second:
            self._colon_visible = not self._colon_visible
            self._last_second = now.second
        
        # Format time with animated colon
        colon = ":" if self._colon_visible else " "
        time_str = f"{now.hour:02d}{colon}{now.minute:02d}{colon}{now.second:02d}"
        
        # Check for alarm
        alarm_icon = ""
        if hasattr(state, 'alerts') and state.alerts.quiet_hours_active:
            alarm_icon = chr(5)  # Custom char index for alarm
        
        # Truncate to fit
        time_str = time_str[:15]
        if alarm_icon:
            time_str = time_str[:14] + alarm_icon
        
        # Format date
        date_str = now.strftime("%b %d, %Y")
        
        # Display
        await lcd_interface.display_text(0, 0, time_str.ljust(16))
        await lcd_interface.display_text(1, 0, date_str.ljust(16))


class IndoorWidget(BaseWidget):
    """
    Page 1: Indoor Climate
    Format:
    Row 0: In:24.5C H:45%
    Row 2: Comfort! :) [custom char]
    """
    
    def __init__(self):
        super().__init__("Indoor")
    
    async def render(self, state: Any, lcd_interface) -> None:
        sensor = state.sensor if hasattr(state, 'sensor') else None
        
        # Get temperature and humidity
        temp = sensor.temperature if sensor and sensor.temperature is not None else "--.-"
        humid = sensor.humidity if sensor and sensor.humidity is not None else "--"
        
        # Format top row: In:24.5C H:45%
        if isinstance(temp, (int, float)):
            temp_str = f"In:{temp:.1f}C"
        else:
            temp_str = f"In:{temp}C"
        
        if isinstance(humid, (int, float)):
            humid_str = f"H:{int(humid)}%"
        else:
            humid_str = f"H:{humid}%"
        
        # Combine and truncate to 16 chars
        top_row = f"{temp_str} {humid_str}"[:16].ljust(16)
        
        # Calculate comfort level for bottom row
        comfort_text = "Comfort!"
        comfort_char = 0  # smile
        
        if sensor and sensor.temperature is not None and sensor.humidity is not None:
            temp_val = float(temp)
            humid_val = float(humid)
            
            if humid_val < 30:
                comfort_text = "Dry :("
                comfort_char = 1  # frown
            elif humid_val > 70:
                comfort_text = "Humid :|"
                comfort_char = 1
            elif temp_val < 18:
                comfort_text = "Cold :("
                comfort_char = 1
            elif temp_val > 28:
                comfort_text = "Hot :|"
                comfort_char = 1
        
        # Bottom row: Comfort comment + custom char
        bottom_row = comfort_text[:15].ljust(15) + chr(comfort_char)
        
        await lcd_interface.display_text(0, 0, top_row)
        await lcd_interface.display_text(1, 0, bottom_row)


class OutdoorWidget(BaseWidget):
    """
    Page 2: Outdoor Weather
    Format:
    Row 0: Out:22.3C Feels:24C
    Row 1: Sunny/Cloudy/Rain
    """
    
    def __init__(self):
        super().__init__("Outdoor")
    
    async def render(self, state: Any, lcd_interface) -> None:
        sensor = state.sensor if hasattr(state, 'sensor') else None
        
        # Get outdoor data (would come from API in real implementation)
        temp = sensor.temperature if sensor and sensor.temperature is not None else "--.-"
        feels = sensor.feels_like if sensor and sensor.feels_like is not None else None
        
        # Format top row
        if isinstance(temp, (int, float)):
            temp_str = f"Out:{temp:.1f}C"
        else:
            temp_str = f"Out:{temp}C"
        
        if feels is not None:
            feels_str = f"Fe:{feels:.0f}C"
        else:
            feels_str = "Fe:--C"
        
        top_row = f"{temp_str} {feels_str}"[:16].ljust(16)
        
        # Bottom row - conditions (would come from API)
        conditions = "Clear"  # Placeholder
        bottom_row = conditions[:16].ljust(16)
        
        await lcd_interface.display_text(0, 0, top_row)
        await lcd_interface.display_text(1, 0, bottom_row)


class AQIWidget(BaseWidget):
    """
    Page 3: Air Quality Index
    Uses short non-truncating words: OK, Mod, Sens, Unhl, VUnh, Hazd
    
    Format:
    Row 0: AQI: 42 [status]
    Row 1: [status word] [icon]
    """
    
    def __init__(self):
        super().__init__("AQI")
        # AQI status mapping - short words that fit on display
        self.status_map = {
            0: ("OK", 2),      # Good - sun icon
            1: ("Mod", 3),     # Moderate - cloud icon
            2: ("Sens", 3),    # Sensitive groups - cloud
            3: ("Unhl", 4),    # Unhealthy - rain
            4: ("VUnh", 4),    # Very Unhealthy - rain
            5: ("Hazd", 5),    # Hazardous - alert
        }
    
    async def render(self, state: Any, lcd_interface) -> None:
        sensor = state.sensor if hasattr(state, 'sensor') else None
        
        aqi = sensor.aqi if sensor and sensor.aqi is not None else 0
        aqi_status = sensor.aqi_status if sensor and sensor.aqi_status else "OK"
        
        # Map AQI value to status
        if aqi <= 50:
            status_idx = 0
        elif aqi <= 100:
            status_idx = 1
        elif aqi <= 150:
            status_idx = 2
        elif aqi <= 200:
            status_idx = 3
        elif aqi <= 300:
            status_idx = 4
        else:
            status_idx = 5
        
        status_word, icon_idx = self.status_map.get(status_idx, ("OK", 2))
        
        # Top row: AQI value
        top_row = f"AQI: {aqi}"[:16].ljust(16)
        
        # Bottom row: Status word + icon
        bottom_row = f"{status_word}".ljust(15) + chr(icon_idx)
        
        await lcd_interface.display_text(0, 0, top_row)
        await lcd_interface.display_text(1, 0, bottom_row)


class SystemWidget(BaseWidget):
    """
    Page 4: System Information
    Shows uptime, API fetch age, disk space, etc.
    
    Format:
    Row 0: Up:2d 4h API:3m
    Row 1: Free:1.2GB [or other info]
    """
    
    def __init__(self):
        super().__init__("System")
    
    async def render(self, state: Any, lcd_interface) -> None:
        system = state.system if hasattr(state, 'system') else None
        sensor = state.sensor if hasattr(state, 'sensor') else None
        
        # Calculate uptime
        uptime_secs = system.uptime_seconds if system and system.uptime_seconds else 0
        days = int(uptime_secs // 86400)
        hours = int((uptime_secs % 86400) // 3600)
        
        if days > 0:
            uptime_str = f"Up:{days}d {hours}h"
        else:
            mins = int(uptime_secs // 60)
            uptime_str = f"Up:{mins}m"
        
        # API fetch age
        api_age = "N/A"
        if sensor and sensor.last_api_fetch:
            delta = datetime.utcnow() - sensor.last_api_fetch
            mins = int(delta.total_seconds() / 60)
            if mins < 1:
                api_age = f"{int(delta.total_seconds())}s"
            else:
                api_age = f"{mins}m"
        
        top_row = f"{uptime_str} API:{api_age}"[:16].ljust(16)
        
        # Disk space or other info
        disk_free = system.disk_free_mb if system and system.disk_free_mb else None
        if disk_free:
            if disk_free >= 1024:
                disk_str = f"Free:{disk_free/1024:.1f}GB"
            else:
                disk_str = f"Free:{int(disk_free)}MB"
        else:
            disk_str = "SkyCast v3.0"
        
        bottom_row = disk_str[:16].ljust(16)
        
        await lcd_interface.display_text(0, 0, top_row)
        await lcd_interface.display_text(1, 0, bottom_row)


class SettingsWidget(BaseWidget):
    """
    Page 5: Settings Menu
    10 settings items that can be scrolled through and adjusted
    
    Settings:
    0. Temp Unit (C/F)
    1. Buzzer Mode (ALL/ALERTS/MUTE)
    2. Screen Power
    3. Auto Scroll
    4. Daily Alarm
    5. Alert Temp Hi
    6. Alert Temp Lo
    7. Sensor Offset
    8. Quiet Hours
    9. Factory Reset
    """
    
    def __init__(self):
        super().__init__("Settings")
        self.settings_list = [
            ("Temp Unit", "C"),
            ("Buzzer", "ALERTS"),
            ("Screen", "ON"),
            ("AutoScroll", "ON"),
            ("Alarm", "OFF"),
            ("Temp Hi", "30C"),
            ("Temp Lo", "5C"),
            ("Offset", "+0.0"),
            ("Quiet", "22-7"),
            ("Reset", "NO"),
        ]
    
    async def render(self, state: Any, lcd_interface) -> None:
        display = state.display if hasattr(state, 'display') else None
        
        settings_index = display.settings_index if display and hasattr(display, 'settings_index') else 0
        
        # Ensure index is valid
        settings_index = max(0, min(settings_index, len(self.settings_list) - 1))
        
        current_setting = self.settings_list[settings_index]
        
        # Top row: Setting name
        name = current_setting[0][:12].ljust(12)
        value = current_setting[1][:3]
        
        top_row = f"{name}:{value}"[:16].ljust(16)
        
        # Bottom row: Navigation hint
        if settings_index == len(self.settings_list) - 1:
            bottom_row = "Hold 3s to reset"
        else:
            bottom_row = "Tap>next Hold>chg"
        
        bottom_row = bottom_row[:16].ljust(16)
        
        await lcd_interface.display_text(0, 0, top_row)
        await lcd_interface.display_text(1, 0, bottom_row)
    
    def cycle_setting(self, index: int) -> str:
        """Cycle through values for a setting"""
        if index >= len(self.settings_list):
            return self.settings_list[index][1]
        
        name, current_value = self.settings_list[index]
        
        # Define value cycles for each setting
        cycles = {
            "Temp Unit": ["C", "F"],
            "Buzzer": ["ALL", "ALERTS", "MUTE"],
            "Screen": ["ON", "OFF"],
            "AutoScroll": ["ON", "OFF"],
            "Alarm": ["OFF", "ON"],
            "Reset": ["NO", "YES"],
        }
        
        if name in cycles:
            values = cycles[name]
            current_idx = values.index(current_value) if current_value in values else 0
            new_value = values[(current_idx + 1) % len(values)]
            self.settings_list[index] = (name, new_value)
            return new_value
        
        return current_value
