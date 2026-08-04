import asyncio
from weather_station.core.state import state
from weather_station.display.widgets import get_widget_text, get_settings_text

async def run_loop(self):
        while True:
            # 1. Check if there is a high-priority system message (Reboot/Shutdown)
            if state.system_message:
                line1, line2 = state.system_message
            
            # 2. Otherwise check Settings Mode
            elif state.in_settings_mode:
                line1, line2 = get_settings_text()
            
            # 3. Otherwise show standard widgets
            else:
                widget = state.custom_pages.get(state.current_page, 
                         self.widget_map.get(state.current_page, "widget_clock"))
                line1, line2 = get_widget_text(widget)
            
            state.last_line1, state.last_line2 = line1, line2
            self.lcd.write_lines(line1, line2)
            await asyncio.sleep(0.2) # Slightly faster refresh for snappier feedback