"""Touch button multi-tap and hold handling."""
import asyncio
import os
import time
from gpiozero import Button
from core.state import state
from hardware.pins import TOUCH_PIN
from persistence.database import save_setting


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
                lcd_driver.write_lines("System Action", "Shutdown...")
                buzzer.beep(on_time=0.15, off_time=0.1, n=4)
                await asyncio.sleep(1.5)
                os.system("sudo shutdown -h now")
                break
            elif duration >= 5.0:
                lcd_driver.write_lines("System Action", "Rebooting...")
                buzzer.beep(on_time=0.15, off_time=0.1, n=3)
                await asyncio.sleep(1.5)
                os.system("sudo reboot")
                break

        else:
            if hold_start_time is not None:
                duration = now - hold_start_time
                hold_start_time = None

                # Short hold inside Settings mode toggles selected row value
                if 1.0 <= duration < 4.0:
                    snap = state.get_snapshot_sync()
                    if snap.in_settings_mode:
                        if snap.settings_page_index == 0:
                            new_unit = "F" if snap.temp_unit == "C" else "C"
                            await state.update(temp_unit=new_unit)
                            await save_setting("temp_unit", new_unit)
                        elif snap.settings_page_index == 1:
                            modes = ["ALL", "ERR", "MUTE"]
                            next_mode = modes[(modes.index(snap.buzzer_mode) + 1) % len(modes)]
                            await state.update(buzzer_mode=next_mode)
                            await save_setting("buzzer_mode", next_mode)
                            
                        buzzer.beep(on_time=0.15, off_time=0.1, n=1)

                elif duration < 0.5:
                    press_count += 1
                    last_press_time = now

        if press_count > 0 and (now - last_press_time) > 0.35:
            snap = state.get_snapshot_sync()

            if press_count == 1:
                if snap.in_settings_mode:
                    next_idx = (snap.settings_page_index + 1) % 2
                    await state.update(settings_page_index=next_idx)
                else:
                    next_page = (snap.current_page % snap.total_pages) + 1
                    await state.update(current_page=next_page)
                
                buzzer.beep(on_time=0.08, off_time=0.08, n=1)

            elif press_count == 3:
                # Toggle Settings Mode with 3 beeps
                new_mode = not snap.in_settings_mode
                await state.update(in_settings_mode=new_mode, settings_page_index=0)
                buzzer.beep(on_time=0.10, off_time=0.08, n=3)

            press_count = 0