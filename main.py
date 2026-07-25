"""Main Supervisor Routine & Hardware Task Loop."""
import asyncio
import uvicorn
from weather_station.app import create_app
from weather_station.config.schema import load_config
from weather_station.core.state import state
from weather_station.display.manager import DisplayManager
from weather_station.hardware.buzzer import get_buzzer
from weather_station.hardware.dht import DHTSensor
from weather_station.hardware.lcd import LCDDriver
from weather_station.input.processor import process_touch_input
from weather_station.persistence.database import init_db, log_sensor_data
from weather_station.services.system_stats import get_pi_stats
from weather_station.services.weather_api import fetch_weather_and_aqi
from weather_station.utils.logging_setup import setup_logging

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