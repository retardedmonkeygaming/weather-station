import asyncio
from weather_station.core.state import state
from weather_station.display.widgets import get_widget_text

class DisplayManager:
    def __init__(self, lcd):
        self.lcd = lcd
        self.widget_map = {
            1: "widget_clock",
            2: "widget_indoor",
            3: "widget_outdoor",
            4: "widget_aqi",
            5: "widget_pi",
            6: "widget_moon"
        }

    async def run_loop(self):
        while True:
            # Check if UI Designer has a custom override, otherwise use default map
            widget_type = state.custom_pages.get(state.current_page, 
                          self.widget_map.get(state.current_page, "widget_clock"))
            
            line1, line2 = get_widget_text(widget_type)
            self.lcd.write_lines(line1, line2)
            await asyncio.sleep(0.5)