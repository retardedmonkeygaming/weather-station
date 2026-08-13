import asyncio
import time
import os
from weather_station.core.state import state
from weather_station.core.config import settings

class InputProcessor:
    """Professional input processor with exact gesture mapping:
    - 1 Tap: Next Page / Scroll Setting
    - 3 Taps: Enter/Leave Settings
    - Hold (<5s): Change Setting Value
    - Hold (5s): Reboot Countdown
    - Hold (10s): Shutdown Countdown
    """

    def __init__(self, sensors, buzzer):
        self.sensors = sensors
        self.buzzer = buzzer
        self.tap_count = 0
        self.last_tap_time = 0
        self.press_start_time = 0
        self.is_processing = False
        self.in_settings_mode = False
        
        # Timing thresholds
        self.debounce_delay = 0.15      # Ignore bounces under 150ms
        self.tap_timeout = 0.4          # Max time between taps to count as multi-tap
        self.hold_threshold = 0.8       # Min time to consider a hold (for value change)
        self.reboot_hold_time = 5.0     # 5 seconds for reboot
        self.shutdown_hold_time = 10.0  # 10 seconds for shutdown
        self.is_holding = False

    async def run_loop(self):
        """Main input processing loop with exact gesture mapping."""
        while True:
            if self.sensors.is_pressed() and not self.is_processing:
                self.is_processing = True
                self.press_start_time = time.time()
                self.is_holding = True
                
                # Check if already in hold state from previous iteration
                notified_reboot = False
                notified_shutdown = False

                # Hold detection loop with real-time feedback
                while self.sensors.is_pressed():
                    elapsed = time.time() - self.press_start_time

                    # 10s hold - Shutdown
                    if elapsed >= self.shutdown_hold_time:
                        if not notified_shutdown:
                            self.buzzer.beep(0.2, repeats=3)
                            notified_shutdown = True
                        state.system_message = ("RELEASE FOR:", "SHUTDOWN")

                    # 5s hold - Reboot
                    elif elapsed >= self.reboot_hold_time:
                        if not notified_reboot:
                            self.buzzer.beep(0.15, repeats=2)
                            notified_reboot = True
                        state.system_message = ("RELEASE FOR:", "REBOOT")

                    # <5s hold in settings - Value change feedback
                    elif elapsed >= self.hold_threshold and self.in_settings_mode:
                        state.system_message = ("ADJUSTING...", "VALUE")

                    await asyncio.sleep(0.05)

                # Button released - calculate duration
                duration = time.time() - self.press_start_time
                state.system_message = None
                self.is_processing = False
                self.is_holding = False

                # Handle hold actions (priority order: shutdown > reboot > adjust)
                if duration >= self.shutdown_hold_time:
                    self.buzzer.beep(0.5, repeats=2)
                    os.system("sudo shutdown -h now")
                    return

                elif duration >= self.reboot_hold_time:
                    self.buzzer.beep(0.3)
                    os.system("sudo reboot")
                    return

                elif duration >= self.hold_threshold:
                    # Short/Medium hold: Change setting value if in settings mode
                    if self.in_settings_mode:
                        self.buzzer.beep(0.1)
                        await self._cycle_setting_value()
                    # If not in settings, ignore short holds
                    
                else:
                    # Valid tap detected (< hold_threshold)
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

            await asyncio.sleep(0.05)

    async def _handle_taps(self):
        """Handle tap gestures for navigation."""
        if self.in_settings_mode:
            # In settings mode: single tap advances to next setting
            state.settings_index += 1
            if state.settings_index > 14:  # Updated for 14 settings
                state.settings_index = 1
            self.buzzer.beep(0.05)
            
            # Triple tap exits settings
            if self.tap_count == 3:
                self.in_settings_mode = False
                state.system_message = ("SETTINGS", "EXITED")
                self.buzzer.beep(0.1, repeats=2)
                state.settings_index = 1
        else:
            # Normal mode
            if self.tap_count == 1:
                # Single tap: next page
                state.current_page += 1
                if state.current_page > state.total_pages:
                    state.current_page = 1
                self.buzzer.beep(0.05)
                
            elif self.tap_count == 3:
                # Triple tap: enter settings
                self.in_settings_mode = True
                state.settings_index = 1
                state.system_message = ("SETTINGS", "ENTERED")
                self.buzzer.beep(0.1, repeats=2)
        
        self.tap_count = 0

    async def _cycle_setting_value(self):
        """Cycle through available values for the current setting."""
        idx = state.settings_index

        if idx == 1:  # Temperature Unit
            settings.unit = "F" if settings.unit == "C" else "C"
            state.system_message = ("Temp Unit:", f"{settings.unit}")

        elif idx == 2:  # Buzzer Mode
            modes = ["ALL", "ALERTS", "MUTE"]
            current_idx = modes.index(settings.buzzer_mode) if settings.buzzer_mode in modes else 0
            settings.buzzer_mode = modes[(current_idx + 1) % len(modes)]
            state.system_message = ("Buzzer:", f"{settings.buzzer_mode}")

        elif idx == 3:  # Screen Power
            state.display_backlight = not getattr(state, 'display_backlight', True)
            state.system_message = ("Screen:", "ON" if state.display_backlight else "OFF")

        elif idx == 4:  # Auto Scroll
            state.auto_scroll = not getattr(state, 'auto_scroll', False)
            state.system_message = ("Auto Scroll:", "ON" if state.auto_scroll else "OFF")

        elif idx == 5:  # Daily Alarm
            state.alarm_enabled = not getattr(state, 'alarm_enabled', False)
            state.system_message = ("Alarm:", "ON" if state.alarm_enabled else "OFF")

        elif idx == 6:  # Alert Temp Hi
            current = getattr(state, 'alert_temp_hi', 35.0)
            state.alert_temp_hi = current + 1.0 if current < 50 else 0
            state.system_message = ("Alert Hi:", f"{state.alert_temp_hi}C")

        elif idx == 7:  # Alert Temp Lo
            current = getattr(state, 'alert_temp_lo', 5.0)
            state.alert_temp_lo = current - 1.0 if current > -10 else 30
            state.system_message = ("Alert Lo:", f"{state.alert_temp_lo}C")

        elif idx == 8:  # Sensor Offset
            current = getattr(state, 'sensor_offset', 0.0)
            state.sensor_offset = current + 0.5 if current < 5 else -5
            state.system_message = ("Offset:", f"{state.sensor_offset:+.1f}")

        elif idx == 9:  # Quiet Hours
            state.quiet_hours = not getattr(state, 'quiet_hours', False)
            state.system_message = ("Quiet Hours:", "ON" if state.quiet_hours else "OFF")

        elif idx == 10:  # Backlight Timeout
            timeouts = [0, 30, 60, 120, 300]  # 0=always on
            current = getattr(state, 'backlight_timeout', 0)
            try:
                idx_current = timeouts.index(current)
                state.backlight_timeout = timeouts[(idx_current + 1) % len(timeouts)]
            except ValueError:
                state.backlight_timeout = 30
            state.system_message = ("Backlight TO:", f"{state.backlight_timeout}s")

        elif idx == 11:  # Data Retention
            days = [7, 14, 30, 60, 90]
            current = getattr(state, 'data_retention_days', 30)
            try:
                idx_current = days.index(current)
                state.data_retention_days = days[(idx_current + 1) % len(days)]
            except ValueError:
                state.data_retention_days = 14
            state.system_message = ("Retention:", f"{state.data_retention_days}d")

        elif idx == 12:  # Demo Mode
            state.demo_mode = not getattr(state, 'demo_mode', False)
            state.system_message = ("Demo Mode:", "ON" if state.demo_mode else "OFF")

        elif idx == 13:  # Discord Alerts
            state.discord_alerts = not getattr(state, 'discord_alerts', False)
            state.system_message = ("Discord:", "ON" if state.discord_alerts else "OFF")

        elif idx == 14:  # Factory Reset
            state.system_message = ("HOLD 3S", "TO RESET")
            # Actual reset handled by separate logic if needed

        # Save setting to database
        from weather_station.persistence.database import DatabaseManager
        db = DatabaseManager()
        if idx == 1:
            await db.save_setting("unit", settings.unit, "hardware")
        elif idx == 2:
            await db.save_setting("buzzer_mode", settings.buzzer_mode, "hardware")
