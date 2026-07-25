"""Touch button multi-tap and hold handling."""
import asyncio
import os
import time
from gpiozero import Button
from core.state import state
from hardware.pins import TOUCH_PIN
from persistence.database import save_setting, factory_reset_db


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
                        idx = snap.settings_page_index
                        
                        if idx == 0:  # Temp Unit
                            new_val = "F" if snap.temp_unit == "C" else "C"
                            await state.update(temp_unit=new_val)
                            await save_setting("temp_unit", new_val)
                            
                        elif idx == 1:  # Buzzer Mode
                            modes = ["ALL", "ERR", "MUTE"]
                            next_m = modes[(modes.index(snap.buzzer_mode) + 1) % len(modes)]
                            await state.update(buzzer_mode=next_m)
                            await save_setting("buzzer_mode", next_m)
                            
                        elif idx == 2:  # Log Interval (60s, 300s, 900s, 3600s)
                            opts = [60, 300, 900, 3600]
                            next_val = opts[(opts.index(snap.log_interval) if snap.log_interval in opts else 1 + 1) % len(opts)]
                            await state.update(log_interval=next_val)
                            await save_setting("log_interval", next_val)
                            
                        elif idx == 3:  # API Fetch Rate (300s, 600s, 1800s)
                            opts = [300, 600, 1800]
                            next_val = opts[(opts.index(snap.api_fetch_interval) if snap.api_fetch_interval in opts else 1 + 1) % len(opts)]
                            await state.update(api_fetch_interval=next_val)
                            await save_setting("api_fetch_interval", next_val)
                            
                        elif idx == 4:  # Temp Offset (-2.0 to +2.0 in 0.5 steps)
                            offsets = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]
                            cur = round(snap.temp_offset, 1)
                            next_off = offsets[(offsets.index(cur) if cur in offsets else 4 + 1) % len(offsets)]
                            await state.update(temp_offset=next_off)
                            await save_setting("temp_offset", next_off)
                            
                        elif idx == 5:  # Night Mode
                            next_nm = not snap.night_mode
                            await state.update(night_mode=next_nm)
                            await save_setting("night_mode", next_nm)
                            
                        elif idx == 6:  # Factory Reset
                            lcd_driver.write_lines("Factory Reset", "Resetting...")
                            await factory_reset_db()
                            await state.update(
                                temp_unit="C", buzzer_mode="ALL", log_interval=300,
                                api_fetch_interval=600, temp_offset=0.0, night_mode=False
                            )
                            buzzer.beep(on_time=0.2, off_time=0.1, n=3)
                            
                        buzzer.beep(on_time=0.15, off_time=0.1, n=1)

                elif duration < 0.5:
                    press_count += 1
                    last_press_time = now

        if press_count > 0 and (now - last_press_time) > 0.35:
            snap = state.get_snapshot_sync()

            if press_count == 1:
                if snap.in_settings_mode:
                    next_idx = (snap.settings_page_index + 1) % snap.total_settings_count
                    await state.update(settings_page_index=next_idx)
                else:
                    next_page = (snap.current_page % snap.total_pages) + 1
                    await state.update(current_page=next_page)
                
                buzzer.beep(on_time=0.08, off_time=0.08, n=1)

            elif press_count == 3:
                new_mode = not snap.in_settings_mode
                await state.update(in_settings_mode=new_mode, settings_page_index=0)
                buzzer.beep(on_time=0.10, off_time=0.08, n=3)

            press_count = 0