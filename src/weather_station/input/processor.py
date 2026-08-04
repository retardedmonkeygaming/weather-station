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
                start = time.time()
                while self.sensors.is_pressed(): await asyncio.sleep(0.05)
                duration = time.time() - start

                if duration > 3.0: # RESET / EXIT
                    state.is_lyric_active = False
                    state.lyric_state = "IDLE"
                    self.buzzer.beep(0.1, repeats=2)
                
                elif duration < 0.6:
                    self.tap_count += 1
                    self.last_tap_time = time.time()

            # EVALUATE GESTURES
            if self.tap_count > 0 and (time.time() - self.last_tap_time) > 0.4:
                # SINGLE TAP
                if self.tap_count == 1:
                    if state.is_lyric_active and state.lyric_state == "MENU":
                        state.selected_song_index = (state.selected_song_index + 1) % len(state.songs_list)
                    else:
                        state.current_page = 1 if state.current_page >= 6 else state.current_page + 1
                
                # DOUBLE TAP (Select Song)
                elif self.tap_count == 2:
                    if state.is_lyric_active and state.lyric_state == "MENU":
                        # Trigger Playback Logic (Coming in next step)
                        pass
                    else:
                        # Enter Lyric Menu from Weather Mode
                        state.is_lyric_active = True
                        state.lyric_state = "MENU"
                        state.songs_list = await self.db.get_all_songs()
                
                # TRIPLE TAP (Stop Playback)
                elif self.tap_count == 3:
                    state.lyric_state = "IDLE"
                    state.is_lyric_active = False

                self.tap_count = 0
            await asyncio.sleep(0.05)