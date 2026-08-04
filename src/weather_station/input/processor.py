import asyncio
import time
import os
from weather_station.core.state import state
from weather_station.core.config import settings

class InputProcessor:
    def __init__(self, sensors, buzzer):
        self.sensors = sensors
        self.buzzer = buzzer
        self.tap_count = 0
        self.last_tap_time = 0

    async def run_loop(self):
        while True:
            if self.sensors.is_pressed():
                self.buzzer.tick()
                press_start = time.time()
                
                # Monitor how long the button is held
                while self.sensors.is_pressed():
                    elapsed = time.time() - press_start
                    
                    # HOLD 5S: Reboot (Restored)
                    if elapsed >= 5.0 and elapsed < 10.0:
                        # Optional: flash a message on LCD if you want, 
                        # but for now, we just wait for release
                        pass 
                    await asyncio.sleep(0.05)
                
                duration = time.time() - press_start

                # ACTION ON RELEASE BASED ON DURATION
                if duration >= 10.0:
                    # Shutdown
                    self.buzzer.beep(0.5, repeats=2)
                    os.system("sudo shutdown -h now")
                elif duration >= 5.0:
                    # Reboot
                    self.buzzer.beep(0.3)
                    os.system("sudo reboot")
                elif duration >= 3.0:
                    # Factory Reset (Hold 3s)
                    if state.in_settings_mode and state.settings_index == 10:
                        self.buzzer.beep(0.1, repeats=3)
                        # We will call a reset function here later
                        state.in_settings_mode = False
                    else:
                        # Toggle Settings Mode
                        state.in_settings_mode = not state.in_settings_mode
                        state.settings_index = 1
                        self.buzzer.beep(0.1, repeats=2)
                elif duration < 0.6:
                    # Standard Taps
                    self.tap_count += 1
                    self.last_tap_time = time.time()

            # Process Taps
            if self.tap_count > 0 and (time.time() - self.last_tap_time) > 0.4:
                if self.tap_count == 1:
                    if state.in_settings_mode:
                        state.settings_index = 1 if state.settings_index >= 10 else state.settings_index + 1
                    else:
                        state.current_page = 1 if state.current_page >= 6 else state.current_page + 1
                self.tap_count = 0
            await asyncio.sleep(0.05)