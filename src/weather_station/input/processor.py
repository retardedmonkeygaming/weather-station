import asyncio
import time
import os
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
                self.buzzer.tick()
                press_start = time.time()
                notified_5s = False
                notified_10s = False
                
                while self.sensors.is_pressed():
                    elapsed = time.time() - press_start
                    
                    # Real-time LCD feedback for holds
                    if elapsed >= 10.0:
                        if not notified_10s:
                            self.buzzer.beep(0.1)
                            notified_10s = True
                        state.system_message = ("RELEASE FOR:", "POWER OFF")
                    elif elapsed >= 5.0:
                        if not notified_5s:
                            self.buzzer.beep(0.1)
                            notified_5s = True
                        state.system_message = ("RELEASE FOR:", "REBOOT SYSTEM")
                    elif elapsed >= 3.0 and state.in_settings_mode and state.settings_index == 10:
                        state.system_message = ("RELEASE TO:", "FACTORY RESET")
                    
                    await asyncio.sleep(0.05)
                
                # Button Released
                duration = time.time() - press_start
                state.system_message = None # Clear the message immediately

                if duration >= 10.0:
                    self.buzzer.beep(0.5, repeats=2)
                    os.system("sudo shutdown -h now")
                elif duration >= 5.0:
                    self.buzzer.beep(0.3)
                    os.system("sudo reboot")
                elif duration >= 3.0:
                    if state.in_settings_mode and state.settings_index == 10:
                        self.buzzer.beep(0.1, repeats=3)
                        # Placeholder for factory reset logic
                        state.in_settings_mode = False
                    else:
                        state.in_settings_mode = not state.in_settings_mode
                        state.settings_index = 1
                        self.buzzer.beep(0.1, repeats=2)
                elif duration < 0.6:
                    # Snappy single tap
                    self.tap_count += 1
                    self.last_tap_time = time.time()

            # Process Tap Logic
            if self.tap_count > 0 and (time.time() - self.last_tap_time) > 0.3:
                if self.tap_count == 1:
                    if state.in_settings_mode:
                        state.settings_index = 1 if state.settings_index >= 10 else state.settings_index + 1
                    else:
                        state.current_page = 1 if state.current_page >= 6 else state.current_page + 1
                self.tap_count = 0
            
            await asyncio.sleep(0.05)