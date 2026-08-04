import asyncio
from weather_station.core.state import state
from weather_station.display.widgets import get_widget_text, get_settings_text

class DisplayManager:
    def __init__(self, lcd):
        self.lcd = lcd
        self.widget_map = {
            1: "widget_clock", 2: "widget_indoor", 3: "widget_outdoor", 
            4: "widget_forecast", 5: "widget_aqi", 6: "widget_moon"
        }

    async def run_loop(self):
        while True:
            try:
                # 1. PRIORITY: System Messages (Reboot/Shutdown)
                if state.system_message:
                    line1, line2 = state.system_message
                
                # 2. PRIORITY: LyricPulse Mode
                elif state.is_lyric_active:
                    if state.lyric_state == "MENU":
                        if not state.songs_list:
                            line1, line2 = "LYRICPULSE".center(16), "NO SONGS FOUND".center(16)
                        else:
                            song = state.songs_list[state.selected_song_index]
                            # Restores your original menu style: [>] Title
                            line1 = f"\x04 {song['title'][:14]}"
                            line2 = f"   {song['artist'][:14]}"
                    elif state.lyric_state == "PLAYING":
                        line1, line2 = state.current_lyric_line1, state.current_lyric_line2
                    else:
                        line1, line2 = "LYRICPULSE".center(16), "READY".center(16)

                # 3. PRIORITY: Settings Menu
                elif state.in_settings_mode:
                    line1, line2 = get_settings_text()
                
                # 4. PRIORITY: Weather Widgets
                else:
                    widget = state.custom_pages.get(
                        state.current_page, 
                        self.widget_map.get(state.current_page, "widget_clock")
                    )
                    line1, line2 = get_widget_text(widget)

                # Update live preview and physical LCD
                state.last_line1, state.last_line2 = line1, line2
                self.lcd.write_lines(line1, line2)
                
            except Exception as e:
                # Prevent total crash if a single widget fails
                self.lcd.write_lines("DISPLAY ERROR", "CHECK LOGS")
            
            await asyncio.sleep(0.1)