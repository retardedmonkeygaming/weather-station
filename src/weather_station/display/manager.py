import asyncio
from weather_station.core.state import state
from weather_station.display.widgets import get_widget_text

class DisplayManager:
    def __init__(self, lcd):
        self.lcd = lcd

    async def run_loop(self):
        while True:
            # Determine which widget to show
            # We check if a custom page is set, otherwise default to a mapping
            widget_map = {1: "widget_clock", 2: "widget_indoor", 3: "widget_outdoor"}
            current_widget = state.custom_pages.get(state.current_page, widget_map.get(state.current_page, "widget_clock"))
            
            line1, line2 = get_widget_text(current_widget)
            
            # Only update if the content actually changes to prevent flickering
            self.lcd.write_lines(line1, line2)
            
            await asyncio.sleep(0.5)