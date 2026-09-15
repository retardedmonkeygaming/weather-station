"""
main.py — entry point: config load, task supervisor, Uvicorn.

Boot sequence:
    1. init_db()                — schema + WAL
    2. load_settings()          — persisted settings & page layouts into state
    3. hardware boot sequence   — splash, one-shot glyph burn, DHT11/WiFi probes
    4. start_background_tasks() — every subsystem under safe_task supervision
    5. run_web_server()         — Uvicorn inside the same event loop

Supervisor:
    safe_task wraps every background coroutine so a crash (DHT11 timing
    timeout, network drop, DB hiccup, LCD I/O error...) is caught cleanly,
    registered in the subsystem health map (surfaced by /api/health and the
    dashboard badge), and the subsystem restarts after a localized cool-down.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List

import config, config_io, database
from config import get_state
from hardware.lcd_driver import get_lcd
from hardware.sensors import (
    ButtonController, buzzer, dht_sensor,
)
from services import discord_bot
from services.moon_phase import calculate_moon_phase
from services.mqtt_client import mqtt_publish_loop
from services.render import build_frame
from services.weather_api import weather_fetch_loop
from utils import is_night_time, safe_float

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("weather.main")


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------

async def safe_task(coro_func: Callable[[], Awaitable[None]],
                    task_name: str) -> None:
    """Run `coro_func` forever, restarting it after a cool-down on crash.

    CancelledError propagates (normal shutdown); every other exception is
    logged, registered in the web-visible health map, and the coroutine is
    restarted after TASK_RESTART_COOLDOWN_S.
    """
    while True:
        try:
            await coro_func()
            log.info("Task '%s' completed", task_name)
            config.mark_subsystem_healthy(task_name)
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("Task '%s' crashed: %s — restarting in %.0fs",
                          task_name, exc, config.TASK_RESTART_COOLDOWN_S)
            config.register_subsystem_failure(task_name, exc)
            # Notification center (ENH 2): surface the crash in the bell icon
            config.push_notification(
                "error", f"{task_name} crashed — restarting: {exc}")
            await asyncio.sleep(config.TASK_RESTART_COOLDOWN_S)


# ---------------------------------------------------------------------------
# Background coroutines
# ---------------------------------------------------------------------------

async def _display_manager() -> None:
    """Render the current frame whenever state changes (screen-on guard)."""
    state = get_state()
    lcd = get_lcd()
    last_rendered = ""
    screen_was_off = False

    while True:
        if state.get_setting("screen") == "OFF":
            if not screen_was_off:
                await lcd.clear()
                screen_was_off = True
                last_rendered = ""
                state.last_lcd_rendered_text = ["SCREEN OFF", ""]
            await asyncio.sleep(0.2)
            continue

        if screen_was_off:
            screen_was_off = False
            state.mark_page_dirty()

        line1, line2 = build_frame(state)

        if (line1, line2) != last_rendered or state.page_changed:
            await lcd.render(line1, line2, clear_first=state.page_changed)
            state.last_lcd_rendered_text = [line1, line2]
            last_rendered = (line1, line2)
            state.page_changed = False

        await asyncio.sleep(0.05)


async def _icon_animator() -> None:
    """Animate the hourglass clock glyph while page 1 is visible."""
    state = get_state()
    while True:
        if state.current_page == 1 and not state.in_settings_mode:
            state.clock_icon_frame = (
                "\x01" if state.clock_icon_frame == "\x00" else "\x00"
            )
            state.mark_page_dirty()
        await asyncio.sleep(0.5)


async def _auto_scroll() -> None:
    """Rotate pages every N seconds when auto-scroll is enabled."""
    state = get_state()
    while True:
        scroll = int(state.get_setting("auto_scroll"))
        if scroll > 0 and not state.in_settings_mode:
            await asyncio.sleep(scroll)
            scroll = int(state.get_setting("auto_scroll"))
            if (scroll > 0 and not state.in_settings_mode
                    and not state.alarm_ringing
                    and not state.temp_alert_active):
                state.current_page = (
                    1 if state.current_page >= state.total_pages
                    else state.current_page + 1
                )
                state.mark_page_dirty()
        else:
            await asyncio.sleep(1.0)


async def _alarm_monitor() -> None:
    """Trigger the daily alarm; pulse the buzzer while it rings."""
    state = get_state()
    lcd = get_lcd()
    shown_ring_frame = False

    while True:
        now = datetime.now()
        if state.get_setting("alarm_on") == "ON":
            if (now.hour == int(state.get_setting("alarm_hr"))
                    and now.minute == int(state.get_setting("alarm_min"))):
                if not state.alarm_ringing and not state.alarm_dismissed_today:
                    state.alarm_ringing = True
                    shown_ring_frame = False
                    state.mark_page_dirty()
                    hr = int(state.get_setting("alarm_hr"))
                    mn = int(state.get_setting("alarm_min"))
                    config.push_notification(
                        "alarm", f"Daily alarm triggered at {hr:02d}:{mn:02d}")
            else:
                state.alarm_dismissed_today = False

        if state.alarm_ringing:
            if not shown_ring_frame:
                await lcd.render("\x02 ALARM TRIGGER ", "Tap to dismiss...")
                state.last_lcd_rendered_text = ["\x02 ALARM TRIGGER ",
                                                "Tap to dismiss..."]
                shown_ring_frame = True
            if not is_night_time(now):
                buzzer.pulse()
            await asyncio.sleep(0.2)
        else:
            await asyncio.sleep(1.0)


async def _db_logger() -> None:
    """Persist a historical reading every log_rate minutes."""
    state = get_state()
    while True:
        await asyncio.sleep(int(state.get_setting("log_rate")) * 60)
        if state.indoor_temp is None or state.dht_error:
            continue
        await database.insert_weather_log(
            state.indoor_temp,
            state.indoor_humid,
            safe_float(state.outdoor_temp),
            safe_float(state.outdoor_humid),
        )


async def _guest_mode_monitor() -> None:
    """Guest Mode (ENH 5): after GUEST_MODE_TIMEOUT_S without a button press,
    dim the LCD (contrast lowered) and silence the buzzer — data keeps
    rendering. Any press restores full contrast instantly."""
    state = get_state()
    lcd = get_lcd()
    was_active = False
    while True:
        if state.get_setting("guest_mode") != "ON":
            if was_active:
                lcd.set_dimmed(False)
                state.guest_active = False
                was_active = False
            await asyncio.sleep(5.0)
            continue

        idle = time.time() - state.last_button_press
        should_dim = idle >= config.GUEST_MODE_TIMEOUT_S

        if should_dim and not state.guest_active:
            state.guest_active = True
            was_active = True
            lcd.set_dimmed(True)
            config.push_notification("info", "Guest Mode engaged — LCD dimmed")
        elif not should_dim and state.guest_active:
            state.guest_active = False
            was_active = False
            lcd.set_dimmed(False)
            config.push_notification("info", "Guest Mode ended — LCD restored")

        await asyncio.sleep(5.0)


# ---------------------------------------------------------------------------
# Hardware boot sequence (blocking-safe: loop is not serving yet)
# ---------------------------------------------------------------------------

async def hardware_boot_sequence() -> None:
    """Splash + progress bar + sensor/network probes, with override on tap."""
    lcd = get_lcd()
    state = get_state()

    line1 = " WEATHER STATION"
    if lcd.is_mock:
        line1 = config.MOCK_BOOT_MESSAGE.center(16).rstrip()
    await lcd.render(line1, " v4.1 Booting...")
    buzzer.beep(0.06, 2, pause=0.08)
    await asyncio.sleep(1.0)

    for i in range(16):
        await lcd.render("Loading System..", "\x06" * (i + 1))
        await asyncio.sleep(0.05)

    # DHT11 probe
    try:
        temp, humid = await dht_sensor.read_once()
        if temp is not None and humid is not None:
            state.indoor_temp_raw = temp
            offset = float(state.get_setting("dht_offset_temp") or 0.0)
            state.indoor_temp = round(temp + offset, 1)
            state.indoor_humid = humid
            state.dht_error = False
        else:
            state.dht_error = True
    except Exception:
        state.dht_error = True

    # Network probe (one-shot)
    state.wifi_error = not await _probe_network()

    # Error gate: hold to override, 5s reboot, 10s shutdown.
    # Only blocks on real hardware — desktop/mock runs proceed for testing.
    if not config.IS_PI:
        if state.dht_error:
            log.warning("DHT11 unavailable (expected on desktop) — continuing")
        if state.wifi_error:
            log.warning("Network probe failed (desktop) — continuing; "
                        "fetch loop will retry")
        # Desktop must never block on the hardware error gate.
        state.dht_error = False
        state.wifi_error = False

    while (state.dht_error or state.wifi_error) and not state.override_active:
        await _render_boot_errors(state)
        buzzer.rapid_error_beep()

        pressed = await _wait_for_press()
        if not pressed:
            continue

        press_start = time.time()
        while await _still_pressed():
            await asyncio.sleep(0.05)
            elapsed = time.time() - press_start
            if elapsed >= 10.0:
                await lcd.render("System Shutdown", "Power Off...")
                buzzer.beep(1.2, force=True)
                import os
                os.system("sudo shutdown -h now")
                return
            if elapsed >= 5.0:
                await lcd.render("System Reboot...", "Please Wait")
                buzzer.beep(0.6, force=True)
                import os
                os.system("sudo reboot")
                return

        if time.time() - press_start < 1.0:
            state.override_active = True
            buzzer.beep(0.1, repeats=2, force=True)

    await lcd.render("System Ready!", "Starting services...")
    await asyncio.sleep(1.0)
    await lcd.clear()
    log.info(
        "Boot done — DHT error: %s, WiFi error: %s (mock LCD: %s)",
        state.dht_error, state.wifi_error, lcd.is_mock,
    )


async def _probe_network() -> bool:
    """One-shot HTTPS reachability check with a 4s timeout."""
    try:
        import aiohttp
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=4)
        ) as session:
            async with session.get(config.OPEN_METEO_FORECAST_URL) as response:
                return response.status == 200
    except Exception:
        return False


async def _render_boot_errors(state) -> None:
    lcd = get_lcd()
    if state.dht_error and state.wifi_error:
        await lcd.render("Error: DHT11", "& WiFi Failure")
    elif state.dht_error:
        await lcd.render("Error: DHT11", "Sensor Missing")
    elif state.wifi_error:
        await lcd.render("Error: WiFi", "Not Connected")


async def _wait_for_press() -> bool:
    """Poll for a button press for up to ~1s."""
    if button_controller is None:
        await asyncio.sleep(1.0)
        return False
    for _ in range(10):
        if button_controller._is_pressed():
            return True
        await asyncio.sleep(0.1)
    return False


async def _still_pressed() -> bool:
    if button_controller is None:
        return False
    return button_controller._is_pressed()


# ---------------------------------------------------------------------------
# Startup wiring
# ---------------------------------------------------------------------------

button_controller: ButtonController | None = None


def start_background_tasks() -> List[asyncio.Task]:
    """Spawn every supervised subsystem task; returns the task list."""
    assert button_controller is not None, "wire ButtonController before tasks"

    specs = [
        (_display_manager, "Display"),
        (button_controller.input_loop, "Input Processor"),
        (_icon_animator, "Icon Animator"),
        (_auto_scroll, "Auto-Scroll"),
        (dht_sensor.polling_loop, "DHT11 Reader"),
        (weather_fetch_loop, "Weather API Fetcher"),
        (_db_logger, "DB Logger"),
        (_alarm_monitor, "Alarm Monitor"),
        (_guest_mode_monitor, "Guest Mode"),
        (mqtt_publish_loop, "MQTT Publisher"),
        (discord_bot.discord_bot_task, "Discord Bot"),
    ]

    return [
        asyncio.create_task(safe_task(fn, name), name=name)
        for fn, name in specs
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    global button_controller

    state = get_state()

    # First-run: make sure the package layout exists and flag the wizard.
    # (The web UI redirects to /setup; pins take effect on next start.)
    config_io.ensure_directories()

    await database.init_db()
    await database.load_settings(state)
    await database.load_page_names(state)
    await database.load_runtime_snapshot(state)

    # Button controller needs the LCD facade; wire before any task starts.
    button_controller = ButtonController(buzzer, get_lcd())

    await hardware_boot_sequence()

    tasks = start_background_tasks()

    # Web server runs in the same loop, supervised like every other task.
    from web.routes import run_web_server
    tasks.append(asyncio.create_task(safe_task(run_web_server, "Web Server")))

    log.info("Weather station running — http://%s:%s (v%s)",
            config.HOST, config.PORT, config.APP_VERSION)

    try:
        await asyncio.gather(*tasks)
    finally:
        await _graceful_shutdown(state)


async def _graceful_shutdown(state) -> None:
    """Persist a runtime snapshot on Ctrl+C / restart so the next boot
    resumes on the same page with the same settings."""
    log.info("Shutting down — saving state snapshot...")
    try:
        await database.save_runtime_snapshot(state)
    except Exception:
        log.exception("Snapshot save failed")
    finally:
        await database.close()


def shutdown_display() -> None:
    """Best-effort final LCD message on interpreter exit."""
    try:
        lcd = get_lcd()
        lcd._backend.message = "System Offline"
        time.sleep(1)
        lcd._backend.clear()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        shutdown_display()
        sys.exit(0)
