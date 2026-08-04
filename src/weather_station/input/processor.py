import asyncio
import time
from weather_station.core.state import state

class InputProcessor:
    def __init__(self, sensors, buzzer):
        self.sensors = sensors
        self.buzzer = buzzer
        self.tap_count = 0
        self.last_tap_time = 0

    async def run_loop(self):
        while True:
            if self.sensors.is_pressed():
                self.buzzer.beep(0.05) # Audible feedback
                start = time.time()
                while self.sensors.is_pressed():
                    await asyncio.sleep(0.05)
                
                duration = time.time() - start
                
                # Tap Logic
                if duration < 0.6:
                    self.tap_count += 1
                    self.last_tap_time = time.time()

            # Process Tap Sequences
            if self.tap_count > 0 and (time.time() - self.last_tap_time) > 0.4:
                if self.tap_count == 1:
                    if state.in_settings_mode:
                        state.settings_index = 1 if state.settings_index >= 10 else state.settings_index + 1
                    else:
                        state.current_page = 1 if state.current_page >= 6 else state.current_page + 1
                elif self.tap_count == 3:
                    state.in_settings_mode = not state.in_settings_mode
                    state.settings_index = 1
                    self.buzzer.beep(0.1, repeats=2)
                
                self.tap_count = 0

            await asyncio.sleep(0.05)