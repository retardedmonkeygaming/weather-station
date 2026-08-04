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
                start_time = time.time()
                while self.sensors.is_pressed():
                    await asyncio.sleep(0.05)
                
                duration = time.time() - start_time
                
                # Logic for long presses
                if duration > 10:
                    self.buzzer.beep(0.5)
                    os.system("sudo shutdown -h now")
                elif duration > 5:
                    self.buzzer.beep(0.2, repeats=2)
                    os.system("sudo reboot")
                else:
                    # Logic for taps
                    self.tap_count += 1
                    self.last_tap_time = time.time()
                    self.buzzer.beep(0.05)

            # Process tap sequences (Single vs Triple)
            if self.tap_count > 0 and (time.time() - self.last_tap_time) > 0.4:
                if self.tap_count == 1:
                    state.current_page = 1 if state.current_page >= state.total_pages else state.current_page + 1
                elif self.tap_count == 3:
                    # Toggle settings mode (logic to be added)
                    pass
                self.tap_count = 0

            await asyncio.sleep(0.05)