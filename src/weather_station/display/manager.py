import asyncio
from weather_station.core.state import state
from weather_station.display.widgets import get_widget_text, get_settings_text

class DisplayManager:
    def __init__(self, lcd):
        self.lcd = lcd
        # Default mapping for the 6 weather pages
        self.widget_map = {
            1: "widget_clock", 
            2: "widget_indoor", 
            3: "widget_outdoor", 
            4: "widget_forecast", 
            5: "widget_aqi", 
            6: "widget_moon"
        }

    async def run_loop(self):
        while True:
            # 1. PRIORITY: System Overrides (Reboot / Shutdown messages)
            if state.system_message:
                line1, line2 = state.system_message
            
            # 2. SECONDARY: Settings Menu
            elif state.in_settings_mode:
                line1, line2 = get_settings_text()
            
            # 3. TERTIARY: Standard Weather Pages
            else:
                # Check if UI Designer has a custom override, else use map
                widget = state.custom_pages.get(
                    state.current_page, 
                    self.widget_map.get(state.current_page, "widget_clock")
                )
                line1, line2 = get_widget_text(widget)
            
            # Update state for WebUI Live View
            state.last_line1, state.last_line2 = line1, line2
            
            # Physical LCD Write
            self.lcd.write_lines(line1, line2)
            
            # Refresh rate (faster for responsive "Release to Reboot" feedback)
            await asyncio.sleep(0.2)