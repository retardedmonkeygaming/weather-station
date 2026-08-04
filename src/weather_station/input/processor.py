import asyncio
import time
import os
from weather_station.core.state import state

class InputProcessor:
    def __init__(self, sensors, buzzer, db):
        self.sensors = sensors
        self.buzzer = buzzer
        self.db = db
        self.tap_count = 0
        self.last_tap_time = 0

    async def run_loop(self):
        while True:
            if self.sensors.is_pressed():
                self.buzzer.tick()
                press_start = time.time()
                
                while self.sensors.is_pressed():
                    elapsed = time.time() - press_start
                    # Visual feedback for holds
                    if elapsed >= 10.0:
                        state.system_message = ("RELEASE FOR:", "POWER OFF")
                    elif elapsed >= 5.0:
                        state.system_message = ("RELEASE FOR:", "REBOOT SYSTEM")
                    elif elapsed >= 3.0:
                        if state.is_lyric_active:
                            state.system_message = ("RELEASE TO:", "EXIT LYRICS")
                        else:
                            state.system_message = ("RELEASE TO:", "OPEN SETTINGS")
                    await asyncio.sleep(0.05)
                
                duration = time.time() - press_start
                state.system_message = None 

                # --- 1. LONG PRESS LOGIC ---
                if duration >= 10.0:
                    self.buzzer.beep(0.5, repeats=2)
                    os.system("sudo shutdown -h now")
                elif duration >= 5.0:
                    self.buzzer.beep(0.3)
                    os.system("sudo reboot")
                elif duration >= 3.0:
                    # THE FIX: Context-aware 3-second hold
                    if state.is_lyric_active:
                        # Exit Lyric Mode back to Weather
                        state.is_lyric_active = False
                        state.lyric_state = "IDLE"
                        self.buzzer.beep(0.1, repeats=2)
                    else:
                        # Enter Weather Settings
                        state.in_settings_mode = not state.in_settings_mode
                        state.settings_index = 1
                        self.buzzer.beep(0.1, repeats=2)
                
                # --- 2. SHORT TAP DETECTION ---
                elif duration < 0.6:
                    self.tap_count += 1
                    self.last_tap_time = time.time()

            # --- 3. GESTURE EVALUATION ---
            if self.tap_count > 0 and (time.time() - self.last_tap_time) > 0.35:
                
                # SINGLE TAP: Next Page / Next Song
                if self.tap_count == 1:
                    if state.in_settings_mode:
                        state.settings_index = 1 if state.settings_index >= 10 else state.settings_index + 1
                    elif state.is_lyric_active and state.lyric_state == "MENU":
                        if state.songs_list:
                            state.selected_song_index = (state.selected_song_index + 1) % len(state.songs_list)
                    else:
                        state.current_page = 1 if state.current_page >= 6 else state.current_page + 1
                
                # DOUBLE TAP: Enter LyricPulse
                elif self.tap_count == 2:
                    if not state.is_lyric_active and not state.in_settings_mode:
                        state.is_lyric_active = True
                        state.lyric_state = "MENU"
                        state.songs_list = await self.db.get_all_songs()
                        state.selected_song_index = 0
                        self.buzzer.beep(0.05, repeats=2)
                
                # TRIPLE TAP: Stop / Cancel
                elif self.tap_count == 3:
                    if state.is_lyric_active:
                        state.is_lyric_active = False
                        state.lyric_state = "IDLE"
                        self.buzzer.error_alert()

                self.tap_count = 0
            await asyncio.sleep(0.05)