"""
sensors.py — DHT11 polling, button input, buzzer mechanics, alarm ring loop.

Encapsulates:
    * Asynchronous DHT11 polling loop (reads via asyncio.to_thread because the
      adafruit_dht pulse-timing reads block) with failure counting, calibration
      offset, 30-min trend tracking, and temp alert triggering.
    * gpiozero Button polling loop: tap pages, triple-tap settings mode,
      hold-to-modify, 5s reboot, 10s shutdown, alarm/alert dismissal.
    * gpiozero Buzzer beeping honoring the buzzer setting + quiet hours.
    * The alarm-ring pulsing loop (driven by main's alarm monitor).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Any, Optional

import config, database
from config import get_state
from utils import (
    is_night_time, next_in_cycle, temp_formatter,
)

log = logging.getLogger("weather.sensors")


# ---------------------------------------------------------------------------
# Buzzer
# ---------------------------------------------------------------------------

class BuzzerController:
    """Buzzer beeps honoring the buzzer setting + quiet-hours policy."""

    def __init__(self) -> None:
        self._buzzer = None
        if config.IS_PI:
            try:
                from gpiozero import Buzzer
                self._buzzer = Buzzer(config.PIN.BUZZER_PIN)
            except Exception:
                log.exception("Buzzer init failed — silent mock active")

    def _allowed(self, force: bool) -> bool:
        if self._buzzer is None:
            return False
        if is_night_time():
            return False
        state = get_state()
        # Guest Mode: stay completely silent while the station is idle-dimmed
        if state.guest_active and not force:
            return False
        mode = state.get_setting("buzzer")
        if mode == "MUTE":
            return False
        if mode == "ERR" and not force:
            return False
        return True

    def pulse(self) -> None:
        """Single non-blocking pulse, used by the alarm ring loop."""
        self._buzzer_on()
        time.sleep(0.1)
        self._buzzer_off()

    def _buzzer_on(self) -> None:
        if self._buzzer is not None:
            try:
                self._buzzer.on()
            except Exception:
                pass

    def _buzzer_off(self) -> None:
        if self._buzzer is not None:
            try:
                self._buzzer.off()
            except Exception:
                pass

    def beep(self, duration: float, repeats: int = 1,
             pause: float = 0.05, force: bool = False) -> None:
        if not self._allowed(force):
            return
        for _ in range(repeats):
            self._buzzer_on()
            time.sleep(duration)          # short blocking ok outside event loop
            self._buzzer_off()
            if repeats > 1:
                time.sleep(pause)

    def rapid_error_beep(self) -> None:
        if not self._allowed(force=True):
            return
        for _ in range(3):
            self._buzzer_on()
            time.sleep(0.15)
            self._buzzer_off()
            time.sleep(0.18)


# ---------------------------------------------------------------------------
# DHT11
# ---------------------------------------------------------------------------

class DHT11Sensor:
    """Async DHT11 reader with failure accounting and alert triggering."""

    def __init__(self, buzzer: BuzzerController) -> None:
        self._buzzer = buzzer
        self._device = None
        if config.IS_PI:
            try:
                import adafruit_dht
                import board
                self._device = adafruit_dht.DHT11(
                    getattr(board, f"D{config.PIN.DHT_PIN}"),
                    use_pulseio=False,
                )
            except Exception:
                log.exception("DHT11 init failed")

    def _read_blocking(self):
        if self._device is None:
            return None, None
        return self._device.temperature, self._device.humidity

    async def read_once(self):
        return await asyncio.to_thread(self._read_blocking)

    # -- main polling loop --------------------------------------------------

    async def polling_loop(self) -> None:
        """Forever-loop DHT11 poller; supervised by main.safe_task."""
        state = get_state()
        failed_attempts = 0

        while True:
            try:
                temp, humid = await self.read_once()
                if temp is not None and humid is not None:
                    self._ingest_reading(state, temp, humid)
                    failed_attempts = 0
                    if state.dht_error:
                        state.dht_error = False
                        state.mark_page_dirty()
                else:
                    failed_attempts += 1
            except Exception:
                failed_attempts += 1

            if failed_attempts >= 10 and not state.dht_error:
                state.dht_error = True
                state.mark_page_dirty()
                self._buzzer.rapid_error_beep()

            await asyncio.sleep(3)

    def _ingest_reading(self, state, temp: float, humid: float) -> None:
        now_t = time.time()
        state.indoor_temp_raw = temp
        offset = float(state.get_setting("dht_offset_temp") or 0.0)
        state.indoor_temp = round(temp + offset, 1)
        state.indoor_humid = humid

        # 30-min rolling trend
        state.temp_history_tracker = [
            (t, v) for (t, v) in state.temp_history_tracker
            if now_t - t <= 1800
        ]
        state.temp_history_tracker.append((now_t, state.indoor_temp))
        if len(state.temp_history_tracker) >= 2:
            diff = state.indoor_temp - state.temp_history_tracker[0][1]
            if diff > 0.5:
                state.temp_trend_symbol = "^"
            elif diff < -0.5:
                state.temp_trend_symbol = "v"
            else:
                state.temp_trend_symbol = "->"

        self._check_temp_alert(state)

        # Voice Mode: announce big temperature shifts (ENH 4)
        if state.get_setting("voice_mode") == "ON":
            try:
                from services.voice import maybe_announce_temp_change
                maybe_announce_temp_change()
            except Exception:
                log.exception("Voice announce failed")

        if state.current_page == 2:
            state.mark_page_dirty()

    def _check_temp_alert(self, state) -> None:
        if state.temp_alert_active:
            return
        fmt = temp_formatter(state.get_setting("unit"))
        # Thresholds are user-configurable (Discord /set-alert, settings DB)
        try:
            high = float(state.get_setting("alert_high"))
        except (TypeError, ValueError):
            high = config.BOOT_TEMP_HIGH_THRESHOLD
        try:
            low = float(state.get_setting("alert_low"))
        except (TypeError, ValueError):
            low = config.BOOT_TEMP_LOW_THRESHOLD
        if state.indoor_temp >= high:
            state.temp_alert_active = True
            state.temp_alert_msg = f"HIGH TEMP ALERT!\nIn: {fmt(state.indoor_temp)}"
            state.mark_page_dirty()
            self._buzzer.beep(0.2, repeats=4, force=True)
            config.push_notification(
                "alert", f"High temperature: {fmt(state.indoor_temp)}")
            self._maybe_voice_alert(state, "High temperature alert")
        elif state.indoor_temp <= low:
            state.temp_alert_active = True
            state.temp_alert_msg = f"LOW TEMP ALERT!\nIn: {fmt(state.indoor_temp)}"
            state.mark_page_dirty()
            self._buzzer.beep(0.2, repeats=4, force=True)
            config.push_notification(
                "alert", f"Low temperature: {fmt(state.indoor_temp)}")
            self._maybe_voice_alert(state, "Low temperature alert")

    @staticmethod
    def _maybe_voice_alert(state, message: str) -> None:
        """Speak the alert when Voice Mode is enabled (ENH 4)."""
        if state.get_setting("voice_mode") == "ON":
            from services.voice import speak
            speak(message)


# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------

class ButtonController:
    """gpiozero Button polling loop implementing the interaction model."""

    def __init__(self, buzzer: BuzzerController, lcd) -> None:
        self._buzzer = buzzer
        self._lcd = lcd
        self._button = None
        self._tap_timestamps: list = []
        if config.IS_PI:
            try:
                from gpiozero import Button
                self._button = Button(
                    config.PIN.BUTTON_PIN,
                    pull_up=False,
                    bounce_time=0.08,
                )
            except Exception:
                log.exception("Button init failed")

    # -- helpers ---------------------------------------------------------------

    def _is_pressed(self) -> bool:
        return self._button is not None and self._button.is_pressed

    def _power(self, command: str) -> None:
        if command == "reboot":
            os.system("sudo reboot")
        elif command == "shutdown":
            os.system("sudo shutdown -h now")

    async def _wait_release(self) -> None:
        while self._is_pressed():
            await asyncio.sleep(0.05)

    # -- main loop ----------------------------------------------------------------

    async def input_loop(self) -> None:
        """Forever-loop input processor; supervised by main.safe_task."""
        state = get_state()

        while True:
            if not self._is_pressed():
                await asyncio.sleep(0.05)
                continue

            state.last_button_press = time.time()
            press_start = time.time()
            setting_modified = False
            reboot_notified = False
            shutdown_notified = False

            while self._is_pressed():
                elapsed = time.time() - press_start

                # Alarm / alert dismissal beats everything
                if state.alarm_ringing or state.temp_alert_active:
                    state.alarm_ringing = False
                    state.temp_alert_active = False
                    state.mark_page_dirty()
                    self._buzzer.beep(0.2, force=True)
                    await self._wait_release()
                    break

                # Settings: hold 1.2-3s cycles the highlighted setting
                if (state.in_settings_mode and 1.2 <= elapsed < 3.0
                        and not setting_modified):
                    setting_modified = True
                    self._buzzer.beep(0.15, force=True)
                    self._cycle_setting(state)
                    state.mark_page_dirty()

                # Settings item 10: hold 3s = factory reset
                elif (state.in_settings_mode
                        and state.settings_index == 10
                        and elapsed >= 3.0 and not setting_modified):
                    setting_modified = True
                    await self._factory_reset_sequence(state)
                    break

                if elapsed >= 10.0 and not shutdown_notified:
                    shutdown_notified = True
                    await self._lcd.render("RELEASE FOR:", "Power Off")
                    self._buzzer.beep(0.2, repeats=2, force=True)
                elif (elapsed >= 5.0 and elapsed < 10.0
                        and not reboot_notified and not state.in_settings_mode):
                    reboot_notified = True
                    await self._lcd.render("RELEASE FOR:", "Reboot System")
                    self._buzzer.beep(0.3, force=True)

                await asyncio.sleep(0.05)

            press_duration = time.time() - press_start

            if press_duration >= 10.0:
                await self._lcd.render("System Shutdown", "Power Off...")
                self._buzzer.beep(1.2, force=True)
                self._power("shutdown")
                return

            if press_duration >= 5.0 and not state.in_settings_mode:
                await self._lcd.render("System Reboot...", "Please Wait")
                self._buzzer.beep(0.6, force=True)
                self._power("reboot")
                return

            if not setting_modified and press_duration < 0.6:
                self._register_tap(state)

            await asyncio.sleep(0.05)

    # -- tap interpretation ------------------------------------------------------

    def _register_tap(self, state) -> None:
        now = time.time()
        self._tap_timestamps = [
            t for t in self._tap_timestamps if now - t < 0.6
        ]
        self._tap_timestamps.append(now)

        if len(self._tap_timestamps) >= 3:
            state.in_settings_mode = not state.in_settings_mode
            state.settings_index = 1
            state.mark_page_dirty()
            self._buzzer.beep(0.12, repeats=3, force=True)
            self._tap_timestamps.clear()
        elif len(self._tap_timestamps) == 1:
            asyncio.create_task(self._single_tap(state))

    async def _single_tap(self, state) -> None:
        await asyncio.sleep(0.35)   # wait to see if a 2nd tap arrives
        if len(self._tap_timestamps) != 1:
            return
        if state.in_settings_mode:
            state.settings_index = (
                1 if state.settings_index >= state.total_settings
                else state.settings_index + 1
            )
        else:
            state.current_page = (
                1 if state.current_page >= state.total_pages
                else state.current_page + 1
            )
        state.mark_page_dirty()
        self._buzzer.beep(0.08)
        # Voice Mode: speak the current conditions on tap (ENH 4)
        if state.get_setting("voice_mode") == "ON":
            try:
                from services.voice import announce_summary
                announce_summary()
            except Exception:
                log.exception("Voice summary failed")
        self._tap_timestamps.clear()

    # -- settings modification -------------------------------------------------

    def _cycle_setting(self, state) -> None:
        """Hold-to-cycle the setting currently highlighted in settings mode."""
        idx = state.settings_index
        cycles = config.SETTING_OPTION_CYCLES

        if idx == 1:
            state.set_setting("unit", next_in_cycle(cycles["unit"],
                                                    state.get_setting("unit")))
        elif idx == 2:
            state.set_setting("buzzer", next_in_cycle(cycles["buzzer"],
                                                      state.get_setting("buzzer")))
        elif idx == 3:
            state.set_setting("screen", next_in_cycle(cycles["screen"],
                                                      state.get_setting("screen")))
        elif idx == 4:
            state.set_setting("auto_scroll", next_in_cycle(cycles["auto_scroll"],
                                                           state.get_setting("auto_scroll")))
        elif idx == 5:
            state.set_setting("alarm_on", next_in_cycle(cycles["alarm_on"],
                                                        state.get_setting("alarm_on")))
        elif idx == 6:
            hr = int(state.get_setting("alarm_hr")) + 1
            state.set_setting("alarm_hr", 0 if hr > 23 else hr)
        elif idx == 7:
            mn = int(state.get_setting("alarm_min")) + 5
            state.set_setting("alarm_min", 0 if mn > 55 else mn)
        elif idx == 8:
            state.set_setting("api_rate", next_in_cycle(cycles["api_rate"],
                                                        state.get_setting("api_rate")))
        elif idx == 9:
            state.set_setting("log_rate", next_in_cycle(cycles["log_rate"],
                                                        state.get_setting("log_rate")))

        key_map = {
            1: "unit", 2: "buzzer", 3: "screen", 4: "auto_scroll",
            5: "alarm_on", 6: "alarm_hr", 7: "alarm_min",
            8: "api_rate", 9: "log_rate",
        }
        key = key_map.get(idx)
        if key:
            asyncio.create_task(
                database.save_setting(key, state.get_setting(key))
            )

    async def _factory_reset_sequence(self, state) -> None:
        self._buzzer.beep(0.4, force=True)
        await self._lcd.render("RESETTING ALL", "SETTINGS...")
        await database.perform_factory_reset(state)
        await asyncio.sleep(1.5)


# ---------------------------------------------------------------------------
# Module-level singletons (GPIO-optional; degrade to no-op mocks off-Pi)
# ---------------------------------------------------------------------------

buzzer = BuzzerController()
dht_sensor = DHT11Sensor(buzzer)
