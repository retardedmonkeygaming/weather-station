import asyncio
import time
import os
from weather_station.core.state import state
from weather_station.core.config import settings

class InputProcessor:
    """Professional input processor with debouncing, gesture recognition, and smooth navigation."""
    
    def __init__(self, sensors, buzzer):
        self.sensors = sensors
        self.buzzer = buzzer
        self.tap_count = 0
        self.last_tap_time = 0
        self.press_start_time = 0
        self.is_processing = False
        self.debounce_delay = 0.15  # Reduced for snappier response
        self.tap_timeout = 0.35     # Time window for multi-tap detection
        self.hold_threshold_short = 0.8   # Short hold for value change in settings
        self.hold_threshold_medium = 3.0  # Medium hold for factory reset
        self.hold_threshold_long = 5.0    # Long hold for reboot
        self.hold_threshold_extra = 10.0  # Extra long hold for shutdown
        
    async def run_loop(self):
        """Main input processing loop with improved responsiveness."""
        while True:
            if self.sensors.is_pressed() and not self.is_processing:
                self.is_processing = True
                self.press_start_time = time.time()
                self.buzzer.tick()
                
                notified_5s = False
                notified_10s = False
                notified_3s = False
                
                # Hold detection loop with real-time feedback
                while self.sensors.is_pressed():
                    elapsed = time.time() - self.press_start_time
                    
                    # System message priority feedback
                    if elapsed >= self.hold_threshold_extra:
                        if not notified_10s:
                            self.buzzer.beep(0.15)
                            notified_10s = True
                        state.system_message = ("RELEASE FOR:", "SHUTDOWN")
                        
                    elif elapsed >= self.hold_threshold_long:
                        if not notified_5s:
                            self.buzzer.beep(0.15)
                            notified_5s = True
                        state.system_message = ("RELEASE FOR:", "REBOOT")
                        
                    elif elapsed >= self.hold_threshold_medium:
                        if not notified_3s:
                            self.buzzer.beep(0.1)
                            notified_3s = True
                        if state.in_settings_mode and state.settings_index == 10:
                            state.system_message = ("RELEASE TO:", "FACTORY RESET")
                    
                    await asyncio.sleep(0.05)
                
                # Button released - calculate duration
                duration = time.time() - self.press_start_time
                state.system_message = None
                self.is_processing = False
                
                # Handle hold actions
                if duration >= self.hold_threshold_extra:
                    self.buzzer.beep(0.5, repeats=2)
                    os.system("sudo shutdown -h now")
                    return
                    
                elif duration >= self.hold_threshold_long:
                    self.buzzer.beep(0.3)
                    os.system("sudo reboot")
                    return
                    
                elif duration >= self.hold_threshold_medium:
                    if state.in_settings_mode and state.settings_index == 10:
                        self.buzzer.beep(0.1, repeats=3)
                        await self._factory_reset()
                        state.in_settings_mode = False
                        state.settings_index = 1
                    else:
                        # Toggle settings mode on medium hold
                        state.in_settings_mode = not state.in_settings_mode
                        state.settings_index = 1
                        self.buzzer.beep(0.1, repeats=2)
                        
                elif duration < self.debounce_delay:
                    # Valid tap detected
                    current_time = time.time()
                    if (current_time - self.last_tap_time) < self.tap_timeout:
                        self.tap_count += 1
                    else:
                        self.tap_count = 1
                    self.last_tap_time = current_time
            
            # Process accumulated taps after timeout
            if self.tap_count > 0 and (time.time() - self.last_tap_time) > self.tap_timeout:
                await self._handle_taps()
                self.tap_count = 0
            
            # Handle settings value adjustment (short hold)
            if state.in_settings_mode and self.sensors.is_pressed() and not self.is_processing:
                await self._handle_settings_adjustment()
            
            await asyncio.sleep(0.05)
    
    async def _handle_taps(self):
        """Handle tap gestures for navigation."""
        if state.in_settings_mode:
            # In settings mode: single tap advances to next setting
            state.settings_index += 1
            if state.settings_index > 10:
                state.settings_index = 1
            self.buzzer.beep(0.05)
        else:
            # Normal mode: single tap advances page
            state.current_page += 1
            if state.current_page > state.total_pages:
                state.current_page = 1
            self.buzzer.beep(0.05)
    
    async def _handle_settings_adjustment(self):
        """Handle short hold in settings mode to adjust values."""
        self.is_processing = True
        hold_start = time.time()
        
        # Wait for short hold threshold
        while self.sensors.is_pressed():
            elapsed = time.time() - hold_start
            if elapsed >= self.hold_threshold_short:
                self.buzzer.beep(0.1)
                await self._cycle_setting_value()
                await asyncio.sleep(0.3)  # Prevent rapid cycling
            await asyncio.sleep(0.05)
        
        self.is_processing = False
    
    async def _cycle_setting_value(self):
        """Cycle through available values for the current setting."""
        idx = state.settings_index
        
        if idx == 1:  # Temperature Unit
            settings.unit = "F" if settings.unit == "C" else "C"
            state.system_message = ("Temp Unit:", f"{settings.unit}")
            
        elif idx == 2:  # Buzzer Mode
            modes = ["ALL", "MUTE", "ALERTS"]
            current_idx = modes.index(settings.buzzer_mode) if settings.buzzer_mode in modes else 0
            settings.buzzer_mode = modes[(current_idx + 1) % len(modes)]
            state.system_message = ("Buzzer:", f"{settings.buzzer_mode}")
            
        elif idx == 3:  # Screen Power (placeholder for auto-dim)
            state.system_message = ("Screen:", "Always ON")
            
        elif idx == 4:  # Auto Scroll
            state.system_message = ("Auto Scroll:", "OFF")
            
        elif idx == 5:  # Daily Alarm
            state.system_message = ("Alarm:", "Disabled")
        
        # Save setting to database
        from weather_station.persistence.database import DatabaseManager
        db = DatabaseManager()
        if idx == 1:
            await db.save_setting("unit", settings.unit, "hardware")
        elif idx == 2:
            await db.save_setting("buzzer_mode", settings.buzzer_mode, "hardware")
    
    async def _factory_reset(self):
        """Perform factory reset."""
        state.system_message = ("RESETTING...", "PLEASE WAIT")
        # Reset all settings to defaults
        settings.unit = "C"
        settings.buzzer_mode = "ALL"
        # Clear database settings
        db = DatabaseManager()
        await db.save_setting("unit", "C", "system")
        await db.save_setting("buzzer_mode", "ALL", "system")
        self.buzzer.beep(0.2, repeats=3)
        state.system_message = ("RESET", "COMPLETE")