"""Touch button multi-tap and hold handling."""
import asyncio
import os
import time
from gpiozero import Button
from weather_station.core.state import state
from weather_station.hardware.pins import TOUCH_PIN


async def process_touch_input(lcd_driver, buzzer):
    button = Button(TOUCH_PIN, pull_up=False)
    press_count = 0
    last_press_time = 0.0
    hold_start_time = None

    while True:
        await asyncio.sleep(0.05)
        now = time.time()

        if button.is_pressed:
            if hold_start_time is None:
                hold_start_time = now

            duration = now - hold_start_time

            if duration >= 10.0:
                lcd_driver.write_lines("System Action", "SHUTDOWN...")
                buzzer.beep(on_time=0.1, off_time=0.1, n=5)
                await asyncio.sleep(2)
                os.system("sudo shutdown -h now")
                break
            elif duration >= 5.0:
                lcd_driver.write_lines("System Action", "REBOOTING...")
                buzzer.beep(on_time=0.1, off_time=0.1, n=3)
                await asyncio.sleep(2)
                os.system("sudo reboot")
                break

        else:
            if hold_start_time is not None:
                duration = now - hold_start_time
                hold_start_time = None

                if duration < 0.5:
                    press_count += 1
                    last_press_time = now

        if press_count > 0 and (now - last_press_time) > 0.4:
            snap = state.get_snapshot_sync()

            if press_count == 1:
                # Cycle display page
                next_page = (snap.current_page % snap.total_pages) + 1
                await state.update(current_page=next_page)
                buzzer.beep(on_time=0.05, off_time=0.05, n=1)

            elif press_count == 3:
                # Toggle Settings Mode
                new_mode = not snap.in_settings_mode
                await state.update(in_settings_mode=new_mode)
                buzzer.beep(on_time=0.08, off_time=0.08, n=2)

            press_count = 0