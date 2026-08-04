import asyncio
from weather_station.core.state import state
from weather_station.display.widgets import get_widget_text, get_settings_text
from dataclasses import dataclass, field
from typing import Optional, Dict, List

class DisplayManager:
    def __init__(self, lcd):
        self.lcd = lcd
        # Default mapping for the 6 weather pages
        self.widget_map = {
            1: "widget_clock", 
            2: "widget_indoor", 
            3: "widget_outdoor", 
            4: "widget_forecast", 
            5: "widget_aqi", 
            6: "widget_moon"
        }

    async def run_loop(self):
        while True:
            # 1. Highest Priority: Are we playing music?
            if state.is_lyric_active:
                line1, line2 = state.current_lyric_line1, state.current_lyric_line2
            
            # 2. Second Priority: System Messages (Reboot/Shutdown)
            elif state.system_message:
                line1, line2 = state.system_message
            
            # 3. Third Priority: Weather Widgets
            else:
                widget = state.custom_pages.get(state.current_page, self.widget_map[state.current_page])
                line1, line2 = get_widget_text(widget)

            self.lcd.write_lines(line1, line2)
            await asyncio.sleep(0.1) # Faster for smooth lyric sync

            # 1. PRIORITY: System Overrides (Reboot / Shutdown messages)
            if state.system_message:
                line1, line2 = state.system_message
            
            # 2. SECONDARY: Settings Menu
            elif state.in_settings_mode:
                line1, line2 = get_settings_text()
            
            # 3. TERTIARY: Standard Weather Pages
            else:
                # Check if UI Designer has a custom override, else use map
                widget = state.custom_pages.get(
                    state.current_page, 
                    self.widget_map.get(state.current_page, "widget_clock")
                )
                line1, line2 = get_widget_text(widget)
            
            # Update state for WebUI Live View
            state.last_line1, state.last_line2 = line1, line2
            
            # Physical LCD Write
            self.lcd.write_lines(line1, line2)
            
            # Refresh rate (faster for responsive "Release to Reboot" feedback)
            await asyncio.sleep(0.2)

            is_lyric_active: bool = False      # False = Weather, True = Lyrics
            lyric_state: str = "IDLE"          # IDLE, MENU, PLAYING
        
            current_song_title: str = ""
            current_song_artist: str = ""
            lyric_line1: str = ""
            lyric_line2: str = ""
        
            # For the LCD song browser
            songs_list: List[Dict] = field(default_factory=list)
            selected_song_index: int = 0

        while True:
            # 1. PRIORITY 1: LYRICPULSE
            if state.is_lyric_active:
                if state.lyric_state == "PLAYING":
                    line1, line2 = state.lyric_line1, state.lyric_line2
                elif state.lyric_state == "MENU":
                    # Replicate your 'display_menu_item' logic
                    song = state.songs_list[state.selected_song_index]
                    line1 = f"\x04 {song['title'][:14]}"
                    line2 = f"  {song['artist'][:14]}"
            
            # 2. PRIORITY 2: SYSTEM MESSAGES
            elif state.system_message:
                line1, line2 = state.system_message
            
            # 3. PRIORITY 3: WEATHER
            else:
                widget = state.custom_pages.get(state.current_page, self.widget_map[state.current_page])
                line1, line2 = get_widget_text(widget)

            self.lcd.write_lines(line1, line2)
            await asyncio.sleep(0.05) # Fast refresh for synced lyrics