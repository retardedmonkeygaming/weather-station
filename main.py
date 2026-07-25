"""Main Supervisor Routine & Hardware Task Loop."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from app import create_app
from config.schema import load_config
from core.state import state
from display.manager import DisplayManager
from hardware.buzzer import get_buzzer
from hardware.dht import DHTSensor
from hardware.lcd import LCDDriver
from input.processor import process_touch_input
from persistence.database import init_db, load_all_settings, log_sensor_data
from services.system_stats import get_pi_stats
from services.weather_api import fetch_weather_and_aqi
from utils.logging_setup import setup_logging

logger = setup_logging()
cfg = load_config()

# Instantiate Hardware Drivers
lcd = LCDDriver()
dht = DHTSensor()
buzzer = get_buzzer()
display_mgr = DisplayManager(lcd)


async def dht_reading_task():
    while True:
        try:
            t, h = dht.read()
            await state.update(indoor_temp=t, indoor_humid=h, dht_error=False)
        except Exception:
            await state.update(dht_error=True)
        await asyncio.sleep(3.0)


async def weather_api_task():
    while True:
        data = await fetch_weather_and_aqi(cfg.latitude, cfg.longitude)
        await state.update(**data)
        await asyncio.sleep(600.0)


async def stats_task():
    while True:
        stats = get_pi_stats()
        await state.update(**stats)
        await asyncio.sleep(2.0)


async def db_logging_task():
    while True:
        await asyncio.sleep(300.0)
        snap = state.get_snapshot_sync()
        await log_sensor_data(snap.model_dump())


async def display_task():
    while True:
        await display_mgr.update_display()
        await asyncio.sleep(0.5)


async def safe_task(coro_func, task_name: str):
    while True:
        try:
            await coro_func()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Task '{task_name}' raised error: {e}. Restarting in 5s...")
            await asyncio.sleep(5)


async def main():
    logger.info("Initializing Database...")
    await init_db(cfg.db_file)
    
    # Restore saved settings from database
    saved_settings = await load_all_settings(cfg.db_file)
    await state.update(
        temp_unit=saved_settings.get("temp_unit", "C"),
        buzzer_mode=saved_settings.get("buzzer_mode", "ALL"),
        auto_scroll_speed=int(saved_settings.get("auto_scroll_speed", "3")),
        alarm_enabled=(saved_settings.get("alarm_enabled") == "True")
    )

    # Boot Loading Sequence with Beeps
    logger.info("Executing boot loading screen sequence...")
    await display_mgr.run_loading_sequence(buzzer)

    # Launch Web App Uvicorn Task
    app = create_app()
    server_config = uvicorn.Config(app, host=cfg.web_host, port=cfg.web_port, log_level="warning")
    server = uvicorn.Server(server_config)

    logger.info("Starting Weather Station Background Supervisor...")
    await asyncio.gather(
        server.serve(),
        safe_task(display_task, "Display"),
        safe_task(dht_reading_task, "DHT Sensor"),
        safe_task(weather_api_task, "Weather API"),
        safe_task(stats_task, "Pi Stats"),
        safe_task(db_logging_task, "DB Logger"),
        safe_task(lambda: process_touch_input(lcd, buzzer), "Touch Input"),
    )


if __name__ == "__main__":
    asyncio.run(main())