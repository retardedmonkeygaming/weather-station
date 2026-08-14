#!/usr/bin/env python3
"""
Weather Station - Main Entry Point
A professional, multi-surface weather station system.

Usage:
    python -m weather_station.main [--mock] [--config CONFIG_FILE]
"""

import asyncio
import argparse
import signal
import sys
from datetime import datetime

from weather_station import AppState, EventSystem, EventType
from weather_station.config.settings import SettingsManager
from weather_station.db.database import DatabaseManager
from weather_station.hardware.drivers import create_hardware, MockMode
from weather_station.utils.helpers import (
    calculate_moon_phase, 
    get_pi_system_stats, 
    parse_aqi_status,
    get_comfort_level
)


class WeatherStation:
    """Main application coordinator"""
    
    def __init__(self, mock_hardware: bool = True):
        self.mock_hardware = mock_hardware
        
        # Core components
        self.state = AppState()
        self.events = EventSystem()
        self.db = DatabaseManager()
        self.settings = SettingsManager()
        self.hardware = None
        
        # Tasks
        self._tasks = []
        self._shutdown = False
    
    async def initialize(self):
        """Initialize all components"""
        print(f"[INIT] Starting Weather Station v{self.state.version}")
        print(f"[INIT] Mock hardware mode: {self.mock_hardware}")
        
        # Set mock mode
        MockMode.ENABLED = self.mock_hardware
        
        # Connect to database
        await self.db.connect()
        await self.db.ensure_tables()
        print("[INIT] Database connected")
        
        # Initialize settings
        self.settings.set_db_manager(self.db)
        await self.settings.initialize()
        print("[INIT] Settings loaded")
        
        # Apply settings to state
        self._apply_settings_to_state()
        
        # Load custom UI pages
        ui_pages = await self.db.load_ui_pages()
        self.state.display.custom_pages = ui_pages
        if ui_pages:
            self.state.display.total_pages = max(6, max(ui_pages.keys()))
        
        # Initialize hardware
        self.hardware = create_hardware(mock=self.mock_hardware)
        await self.hardware["dht_sensor"].initialize()
        print("[INIT] Hardware initialized")
        
        # Log boot event
        await self.db.log_event("SYSTEM_BOOT", "main", f"Mock={self.mock_hardware}")
        
        # Update state
        self.state.status = type(self.state.status).RUNNING
        self.state.hardware.screen_on = self.settings.get("screen_on", True)
        
        # Publish boot event
        await self.events.publish(EventType.SYSTEM_BOOT, {
            "version": self.state.version,
            "mock_mode": self.mock_hardware
        })
        
        print("[INIT] Initialization complete")
    
    def _apply_settings_to_state(self):
        """Apply loaded settings to app state"""
        self.state.location.latitude = self.settings.get("latitude", "29.325390")
        self.state.location.longitude = self.settings.get("longitude", "48.019562")
        self.state.temp_offset = self.settings.get("temp_offset", 0.0)
        self.state.temp_high_threshold = self.settings.get("temp_high_threshold", 32.0)
        self.state.temp_low_threshold = self.settings.get("temp_low_threshold", 10.0)
        self.state.alarm.enabled = self.settings.get("alarm_enabled", False)
        self.state.alarm.hour = self.settings.get("alarm_hour", 17)
        self.state.alarm.minute = self.settings.get("alarm_minute", 0)
        self.state.display.auto_scroll_interval = self.settings.get("auto_scroll_interval", 0)
        self.state.display.auto_scroll_enabled = self.state.display.auto_scroll_interval > 0
    
    async def run(self):
        """Run the main application loop"""
        await self.initialize()
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._sensor_reader_task()),
            asyncio.create_task(self._weather_fetcher_task()),
            asyncio.create_task(self._database_logger_task()),
            asyncio.create_task(self._display_task()),
            asyncio.create_task(self._input_processor_task()),
            asyncio.create_task(self._alarm_monitor_task()),
            asyncio.create_task(self._moon_updater_task()),
        ]
        
        print("[RUN] All tasks started")
        print("[RUN] Weather station is running. Press Ctrl+C to stop.")
        
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        print("\n[SHUTDOWN] Initiating graceful shutdown...")
        
        self._shutdown = True
        self.state.status = type(self.state.status).SHUTDOWN
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.sleep(0.5)
        
        # Clear LCD
        if self.hardware and "lcd" in self.hardware:
            self.hardware["lcd"].clear()
            self.hardware["lcd"].message = "System Offline"
            await asyncio.sleep(1)
            self.hardware["lcd"].clear()
        
        # Turn off buzzer
        if self.hardware and "buzzer" in self.hardware:
            self.hardware["buzzer"].off()
        
        # Log shutdown event
        await self.db.log_event("SYSTEM_SHUTDOWN", "main", "Graceful shutdown")
        
        # Close database
        await self.db.close()
        
        print("[SHUTDOWN] Complete")
    
    async def _sensor_reader_task(self):
        """Read DHT sensor periodically"""
        failed_attempts = 0
        
        while not self._shutdown:
            try:
                reading = await self.hardware["dht_sensor"].read()
                
                if reading.get("error"):
                    failed_attempts += 1
                    if failed_attempts >= 10 and not self.state.hardware.dht_error:
                        self.state.hardware.dht_error = True
                        await self.events.publish(EventType.DHT_ERROR)
                else:
                    temp_raw = reading["temperature"]
                    humidity = reading["humidity"]
                    
                    # Apply calibration offset
                    temp_calibrated = round(temp_raw + self.state.temp_offset, 1)
                    
                    # Update state
                    self.state.sensors.indoor_temp_raw = temp_raw
                    self.state.sensors.indoor_temp = temp_calibrated
                    self.state.sensors.indoor_humidity = humidity
                    self.state.sensors.last_updated = datetime.now()
                    
                    failed_attempts = 0
                    
                    if self.state.hardware.dht_error:
                        self.state.hardware.dht_error = False
                        await self.events.publish(EventType.DHT_RECOVERED)
                    
                    # Track temperature history
                    now = datetime.now().timestamp()
                    self.state.temp_history.append((now, temp_calibrated))
                    # Keep only last 30 minutes
                    cutoff = now - 1800
                    self.state.temp_history = [(t, v) for t, v in self.state.temp_history if t > cutoff]
                    
                    # Check thresholds
                    await self._check_temperature_alerts(temp_calibrated)
                    
                    await self.events.publish(EventType.SENSOR_UPDATED, {
                        "temperature": temp_calibrated,
                        "humidity": humidity
                    })
                
            except Exception as e:
                print(f"[SENSOR] Error: {e}")
                failed_attempts += 1
            
            await asyncio.sleep(3)
    
    async def _check_temperature_alerts(self, temp: float):
        """Check if temperature exceeds thresholds"""
        if temp >= self.state.temp_high_threshold:
            if not self.state.alert.is_active:
                self.state.alert.is_active = True
                self.state.alert.alert_type = "temperature_high"
                self.state.alert.message = f"HIGH TEMP: {temp:.1f}C"
                self.state.alert.triggered_at = datetime.now()
                await self.events.publish(EventType.ALERT_TRIGGERED, {
                    "type": "high_temp",
                    "value": temp
                })
        elif temp <= self.state.temp_low_threshold:
            if not self.state.alert.is_active:
                self.state.alert.is_active = True
                self.state.alert.alert_type = "temperature_low"
                self.state.alert.message = f"LOW TEMP: {temp:.1f}C"
                self.state.alert.triggered_at = datetime.now()
                await self.events.publish(EventType.ALERT_TRIGGERED, {
                    "type": "low_temp",
                    "value": temp
                })
    
    async def _weather_fetcher_task(self):
        """Fetch outdoor weather from API"""
        import aiohttp
        
        interval = self.settings.get("api_fetch_interval", 10) * 60
        timeout = aiohttp.ClientTimeout(total=8)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while not self._shutdown:
                try:
                    weather_url, aqi_url = self.state.get_api_urls()
                    
                    # Fetch weather
                    async with session.get(weather_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'current' in data:
                                self.state.sensors.outdoor_temp = float(data['current']['temperature_2m'])
                                self.state.sensors.outdoor_humidity = int(data['current']['relative_humidity_2m'])
                                self.state.sensors.uv_index = float(data['current']['uv_index'])
                                self.state.sensors.weather_code = int(data['current'].get('weather_code', 0))
                            
                            if 'daily' in data:
                                self.state.sensors.outdoor_temp_min = float(data['daily']['temperature_2m_max'][0])
                                self.state.sensors.outdoor_temp_max = float(data['daily']['temperature_2m_min'][0])
                                self.state.sensors.uv_index_max = float(data['daily']['uv_index_max'][0])
                    
                    # Fetch AQI
                    async with session.get(aqi_url) as response:
                        if response.status == 200:
                            aqi_data = await response.json()
                            if 'current' in aqi_data:
                                self.state.sensors.aqi = int(aqi_data['current']['us_aqi'])
                                self.state.sensors.pm2_5 = float(aqi_data['current']['pm2_5'])
                                self.state.sensors.pm10 = float(aqi_data['current']['pm10'])
                                self.state.sensors.aqi_status = parse_aqi_status(self.state.sensors.aqi)
                    
                    self.state.hardware.wifi_error = False
                    await self.events.publish(EventType.WEATHER_FETCHED)
                    
                except Exception as e:
                    print(f"[WEATHER] Error: {e}")
                    if not self.state.hardware.wifi_error:
                        self.state.hardware.wifi_error = True
                        await self.events.publish(EventType.WEATHER_ERROR, {"error": str(e)})
                
                await asyncio.sleep(interval)
    
    async def _database_logger_task(self):
        """Log sensor data to database"""
        interval = self.settings.get("log_interval", 15) * 60
        
        while not self._shutdown:
            await asyncio.sleep(interval)
            
            if self.state.sensors.indoor_temp is not None and not self.state.hardware.dht_error:
                try:
                    await self.db.log_weather(
                        in_temp=self.state.sensors.indoor_temp,
                        in_humid=self.state.sensors.indoor_humidity,
                        out_temp=self.state.sensors.outdoor_temp,
                        out_humid=self.state.sensors.outdoor_humidity,
                        aqi=self.state.sensors.aqi,
                        pm2_5=self.state.sensors.pm2_5,
                        pm10=self.state.sensors.pm10
                    )
                    await self.events.publish(EventType.LOG_ENTRY_ADDED)
                except Exception as e:
                    print(f"[DB] Log error: {e}")
    
    async def _display_task(self):
        """Update LCD display"""
        last_message = ""
        
        while not self._shutdown:
            if not self.state.hardware.screen_on:
                if last_message != "SCREEN_OFF":
                    self.hardware["lcd"].clear()
                    last_message = "SCREEN_OFF"
                await asyncio.sleep(0.2)
                continue
            
            # Build display message based on current page
            message = self._build_display_message()
            
            if message != last_message or self.state.display.current_page != last_message:
                self.hardware["lcd"].message = message
                self.state.display.last_rendered_lines = message.split("\n")[:2]
                last_message = message
            
            await asyncio.sleep(0.1)
    
    def _build_display_message(self) -> str:
        """Build LCD message based on current state"""
        # Alert override
        if self.state.alert.is_active:
            return self.state.alert.message
        
        # Alarm override
        if self.state.alarm.ringing:
            return f"\x02 ALARM TRIGGER\nTime: {self.state.alarm.hour:02d}:{self.state.alarm.minute:02d}"
        
        # Settings mode
        if self.state.display.in_settings_mode:
            return self._build_settings_message()
        
        # Normal pages
        page = self.state.display.current_page
        
        # Check for custom page
        if page in self.state.display.custom_pages:
            widget = self.state.display.custom_pages[page]
            return self._render_widget(widget)
        
        # Default pages
        if page == 1:
            now = datetime.now()
            alarm_icon = "\x02 " if self.state.alarm.enabled else ""
            return f"{now.strftime('%H:%M:%S')}\n{alarm_icon}{now.strftime('%d-%m-%Y')}"
        
        elif page == 2:
            if self.state.hardware.dht_error:
                return "In: ERR [DHT11]\nState: Check"
            t = self.state.sensors.indoor_temp
            h = self.state.sensors.indoor_humidity
            comfort = get_comfort_level(t, h)
            return f"In:{t:.1f}C H:{h}%\n{comfort}"
        
        elif page == 3:
            t = self.state.sensors.outdoor_temp
            h = self.state.sensors.outdoor_humidity
            status = " [OFF]" if self.state.hardware.wifi_error else ""
            return f"Out:{t:.1f}C {h}%{status}\nWeather"
        
        elif page == 4:
            min_t = self.state.sensors.outdoor_temp_min
            max_t = self.state.sensors.outdoor_temp_max
            return f"L:{min_t:.0f} H:{max_t:.0f}\nUV:{self.state.sensors.uv_index}"
        
        elif page == 5:
            aqi = self.state.sensors.aqi
            status = "!" if self.state.hardware.wifi_error else ""
            return f"AQI:{aqi}{status}\nPM2.5:{self.state.sensors.pm2_5:.0f}"
        
        elif page == 6:
            phase = self.state.moon.short_name
            illum = self.state.moon.illumination
            return f"Moon: {phase}\nIllum: {illum}%"
        
        return "Page Error\nContact Admin"
    
    def _build_settings_message(self) -> str:
        """Build settings menu message"""
        idx = self.state.display.settings_index
        groups = self.settings.get_groups()
        
        # Map index to setting
        settings_list = [
            ("1. Temp Unit", "unit", lambda: self.settings.get("unit", "C")),
            ("2. Buzzer", "buzzer_mode", lambda: self.settings.get("buzzer_mode", "ALL")),
            ("3. Screen", "screen_on", lambda: "ON" if self.settings.get("screen_on", True) else "OFF"),
            ("4. Auto-Scroll", "auto_scroll_interval", lambda: f"{self.settings.get('auto_scroll_interval', 0)}s"),
            ("5. Alarm", "alarm_enabled", lambda: "ON" if self.settings.get("alarm_enabled", False) else "OFF"),
            ("6. Alarm Hr", "alarm_hour", lambda: f"{self.settings.get('alarm_hour', 17):02d}"),
            ("7. Alarm Min", "alarm_minute", lambda: f"{self.settings.get('alarm_minute', 0):02d}"),
            ("8. API Rate", "api_fetch_interval", lambda: f"{self.settings.get('api_fetch_interval', 10)}m"),
            ("9. Log Rate", "log_interval", lambda: f"{self.settings.get('log_interval', 15)}m"),
            ("10. Factory Reset", "factory_reset", lambda: "HOLD 3S"),
        ]
        
        if idx <= len(settings_list):
            label, key, getter = settings_list[idx - 1]
            value = getter()
            return f"{label}\n> {value}"
        
        return "Settings\nEnd of menu"
    
    def _render_widget(self, widget_type: str) -> str:
        """Render a specific widget"""
        if widget_type == "widget_clock":
            now = datetime.now()
            return f"{now.strftime('%H:%M:%S')}\n{now.strftime('%d-%m-%Y')}"
        
        elif widget_type == "widget_indoor":
            t = self.state.sensors.indoor_temp
            h = self.state.sensors.indoor_humidity
            return f"In:{t:.1f}C H:{h}%\nIndoor"
        
        elif widget_type == "widget_outdoor":
            t = self.state.sensors.outdoor_temp
            h = self.state.sensors.outdoor_humidity
            return f"Out:{t:.1f}C {h}%\nOutdoor"
        
        elif widget_type == "widget_aqi":
            aqi = self.state.sensors.aqi
            return f"AQI:{aqi}\n{self.state.sensors.aqi_status}"
        
        elif widget_type == "widget_moon":
            return f"Moon: {self.state.moon.short_name}\n{self.state.moon.illumination}%"
        
        elif widget_type == "widget_pi":
            stats = get_pi_system_stats()
            return f"CPU:{stats['cpu_temp']}\nRAM:{stats['ram_usage']}"
        
        return "Widget\nUnknown"
    
    async def _input_processor_task(self):
        """Process button input"""
        tap_timestamps = []
        
        while not self._shutdown:
            if self.hardware["button"].is_pressed:
                press_start = datetime.now()
                
                while self.hardware["button"].is_pressed:
                    elapsed = (datetime.now() - press_start).total_seconds()
                    
                    # Long press handling
                    if elapsed >= 10:
                        await self.shutdown()
                        print("[INPUT] Shutdown requested")
                        return
                    elif elapsed >= 5:
                        print("[INPUT] Reboot requested")
                        # In real system: os.system("sudo reboot")
                        return
                    
                    await asyncio.sleep(0.05)
                
                press_duration = (datetime.now() - press_start).total_seconds()
                
                # Short tap
                if press_duration < 0.6:
                    now = datetime.now().timestamp()
                    tap_timestamps = [t for t in tap_timestamps if (now - t) < 0.6]
                    tap_timestamps.append(now)
                    
                    if len(tap_timestamps) == 3:
                        # Triple tap - toggle settings mode
                        self.state.display.in_settings_mode = not self.state.display.in_settings_mode
                        self.state.display.settings_index = 1
                        await self.events.publish(
                            EventType.SETTINGS_MODE_ENTERED if self.state.display.in_settings_mode 
                            else EventType.SETTINGS_MODE_EXITED
                        )
                        tap_timestamps.clear()
                    elif len(tap_timestamps) == 1:
                        # Single tap - next page or setting
                        if self.state.display.in_settings_mode:
                            self.state.display.settings_index = min(
                                self.state.display.settings_index + 1, 10
                            )
                        else:
                            self.state.display.current_page = (
                                self.state.display.current_page % self.state.display.total_pages
                            ) + 1
                        await self.events.publish(EventType.PAGE_CHANGED)
                        tap_timestamps.clear()
            
            await asyncio.sleep(0.05)
    
    async def _alarm_monitor_task(self):
        """Monitor and trigger daily alarm"""
        last_check = None
        
        while not self._shutdown:
            now = datetime.now()
            
            if (now.hour == self.state.alarm.hour and 
                now.minute == self.state.alarm.minute and
                last_check != (now.hour, now.minute)):
                
                if self.state.alarm.enabled and not self.state.alarm.dismissed_today:
                    self.state.alarm.ringing = True
                    await self.events.publish(EventType.ALARM_RINGING)
                
                last_check = (now.hour, now.minute)
            else:
                self.state.alarm.dismissed_today = False
            
            if self.state.alarm.ringing:
                # Ring buzzer
                if not self.state.is_night_time():
                    await self.hardware["buzzer"].beep(0.1, repeats=2, pause=0.1)
                await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(1)
    
    async def _moon_updater_task(self):
        """Update moon phase data"""
        while not self._shutdown:
            phase, short, illum, age = calculate_moon_phase()
            self.state.moon.phase_name = phase
            self.state.moon.short_name = short
            self.state.moon.illumination = illum
            self.state.moon.age_days = age
            await asyncio.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="Weather Station System")
    parser.add_argument("--mock", action="store_true", help="Use mock hardware")
    parser.add_argument("--config", type=str, help="Path to config file")
    args = parser.parse_args()
    
    station = WeatherStation(mock_hardware=args.mock)
    
    # Setup signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def signal_handler():
        for task in asyncio.all_tasks(loop):
            task.cancel()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        loop.run_until_complete(station.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
