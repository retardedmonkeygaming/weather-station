"""Main Supervisor Routine & Hardware Task Loop."""
import asyncio
import os
import sys

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
from services.notifications import check_alerts_loop
from services.system_stats import get_pi_stats
from services.weather_api import fetch_weather_and_aqi
from utils.logging_setup import setup_logging
from web.routes import api, dashboard, designer

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

    saved_settings = await load_all_settings(cfg.db_file)
    updates = {}
    
    for k, v in saved_settings.items():
        if k in ["temp_offset", "high_temp_threshold", "low_temp_threshold"]:
            updates[k] = float(v)
        elif k in ["log_interval", "api_fetch_interval", "auto_scroll_speed"]:
            updates[k] = int(v)
        elif k == "night_mode":
            updates[k] = v.lower() == "true"
        elif k == "alarm_enabled":
            updates[k] = v.lower() == "true"
        elif k == "enabled_pages":
            updates[k] = [int(p) for p in v.split(",") if p.isdigit()]
        else:
            updates[k] = v

    await state.update(**updates)

    logger.info("Running hardware diagnostics & startup screens...")
    await display_mgr.run_diagnostics_and_boot(dht, buzzer)

    # Initialize Application & Include Web/API Routers
    app = create_app()
    app.include_router(api.router)
    app.include_router(dashboard.router)
    app.include_router(designer.router)

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
        safe_task(check_alerts_loop, "Alert Notifications"),
        safe_task(lambda: process_touch_input(lcd, buzzer), "Touch Input"),
    )


if __name__ == "__main__":
    asyncio.run(main())