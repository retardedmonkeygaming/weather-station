import asyncio
import time
import os
from weather_station.core.state import state

class InputProcessor:
    def __init__(self, sensors, buzzer, db):
        self.sensors = sensors
        self.buzzer = buzzer
        self.db = db # Needed to fetch song list on double-tap
        self.tap_count = 0
        self.last_tap_time = 0

    async def run_loop(self):
        """The main input loop called by main.py"""
        while True:
            if self.sensors.is_pressed():
                self.buzzer.tick() # Tactile feedback
                press_start = time.time()
                
                # Feedback logic while holding
                while self.sensors.is_pressed():
                    elapsed = time.time() - press_start
                    if elapsed >= 10.0:
                        state.system_message = ("RELEASE FOR:", "POWER OFF")
                    elif elapsed >= 5.0:
                        state.system_message = ("RELEASE FOR:", "REBOOT SYSTEM")
                    await asyncio.sleep(0.05)
                
                duration = time.time() - press_start
                state.system_message = None # Clear hold message

                # 1. LONG PRESS LOGIC
                if duration >= 10.0:
                    self.buzzer.beep(0.5, repeats=2)
                    os.system("sudo shutdown -h now")
                elif duration >= 5.0:
                    self.buzzer.beep(0.3)
                    os.system("sudo reboot")
                elif duration >= 1.5:
                    # Long press (1.5s - 5s) exits LyricPulse mode
                    if state.is_lyric_active:
                        state.is_lyric_active = False
                        state.lyric_state = "IDLE"
                        self.buzzer.beep(0.1, repeats=2)
                
                # 2. TAP LOGIC (Short clicks)
                elif duration < 0.6:
                    self.tap_count += 1
                    self.last_tap_time = time.time()

            # --- PROCESS TAP SEQUENCES ---
            if self.tap_count > 0 and (time.time() - self.last_tap_time) > 0.4:
                
                # SINGLE TAP: Next Weather Page / Next Song
                if self.tap_count == 1:
                    if state.is_lyric_active and state.lyric_state == "MENU":
                        # Scroll LyricPulse Song List
                        if state.songs_list:
                            state.selected_song_index = (state.selected_song_index + 1) % len(state.songs_list)
                    else:
                        # Scroll Weather Pages
                        state.current_page = 1 if state.current_page >= 6 else state.current_page + 1
                
                # DOUBLE TAP: Enter Lyric Menu / Select Song
                elif self.tap_count == 2:
                    if not state.is_lyric_active:
                        # Switch to Lyric Mode and load library
                        state.is_lyric_active = True
                        state.lyric_state = "MENU"
                        state.songs_list = await self.db.get_all_songs()
                        self.buzzer.beep(0.05, repeats=2)
                    elif state.lyric_state == "MENU":
                        # Select the song (Playback logic handled in next step)
                        self.buzzer.beep(0.2)
                        # trigger_playback(state.songs_list[state.selected_song_index]['id'])
                
                # TRIPLE TAP: Kill LyricPulse / Emergency Stop
                elif self.tap_count == 3:
                    state.is_lyric_active = False
                    state.lyric_state = "IDLE"
                    self.buzzer.error_alert()

                self.tap_count = 0
            
            await asyncio.sleep(0.05)