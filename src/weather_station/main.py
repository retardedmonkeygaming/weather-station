"""SkyCast Weather Station - Professional multi-surface weather monitoring.

This is the main entry point for the application.
Run with: python -m weather_station.main
Or use the console script: skycast
"""

__version__ = "3.0.0"
__author__ = "SkyCast Team"

# No imports here to avoid circular dependencies
# Import modules directly where needed
import asyncio
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv


# --- 1. ENVIRONMENT LOAD ---
current_dir = Path(__file__).resolve().parent  # weather_station/
src_dir = current_dir.parent                   # src/
root_dir = src_dir.parent                      # weather-station/
env_path = root_dir / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Try current directory as fallback
    load_dotenv()


# --- 2. IMPORTS ---
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.utils.logging_setup import setup_logging
from weather_station.persistence.database import DatabaseManager
from weather_station.hardware import WeatherLCD, WeatherSensors, WeatherBuzzer
from weather_station.services import WeatherService, SystemService
from weather_station.display.manager import DisplayManager
from weather_station.input.processor import InputProcessor
from weather_station.web.app import app
from weather_station.services.discord_bot import WeatherBot


# --- 3. LOGGING SETUP ---
setup_logging()
logger = logging.getLogger("Main")


# --- 4. BACKGROUND TASK DEFINITIONS ---


async def weather_fetcher(service: WeatherService) -> None:
    """Periodically fetches data from Open-Meteo."""
    while True:
        try:
            await service.fetch_all()
            state.last_api_fetch = __import__("datetime").datetime.now()
        except Exception as e:
            logger.error(f"Weather fetch error: {e}")
            state.wifi_error = True
        await asyncio.sleep(settings.api_rate * 60)


async def dht_reader(sensors: WeatherSensors) -> None:
    """Periodically reads the local DHT11 sensor."""
    while True:
        try:
            temp, humid = sensors.read_dht()
            if temp is not None:
                state.indoor_temp_raw = temp
                state.indoor_temp = temp + settings.dht_temp_offset
                state.indoor_humid = humid
                state.dht_error = False
            else:
                state.dht_error = True
        except Exception as e:
            logger.error(f"DHT read error: {e}")
            state.dht_error = True
        await asyncio.sleep(3)


async def data_logger(db: DatabaseManager) -> None:
    """Periodically logs weather data to database."""
    while True:
        try:
            if state.indoor_temp is not None and state.outdoor_temp != "N/A":
                await db.save_weather_log(
                    in_temp=float(state.indoor_temp),
                    in_humid=float(state.indoor_humid or 0),
                    out_temp=float(state.outdoor_temp),
                    out_humid=float(state.outdoor_humid or 0)
                )
                state.last_log_time = __import__("datetime").datetime.now()
        except Exception as e:
            logger.error(f"Database log error: {e}")
        await asyncio.sleep(settings.log_rate * 60)


async def run_diagnostics(lcd: WeatherLCD, sensors: WeatherSensors, buzzer: WeatherBuzzer, weather: WeatherService) -> None:
    """Boot sequence diagnostics with visual feedback."""
    logger.info("Running Diagnostics...")
    lcd.clear()
    lcd.write_lines(" WEATHER STATION", " v3.0 Booting...")
    buzzer.beep(0.06, repeats=2)
    await asyncio.sleep(1.2)

    lcd.clear()
    for i in range(16):
        lcd.write_lines("Loading System..", "\x06" * (i + 1))
        await asyncio.sleep(0.08)

    # Sensor Check
    temp, _ = sensors.read_dht()
    if temp is None:
        logger.warning("DHT11 not detected during boot.")
        lcd.write_lines("Error: DHT11", "Check Sensor")
        buzzer.error_alert()
        await asyncio.sleep(2)

    # WiFi/API Check
    try:
        await weather.fetch_all()
        if state.wifi_error:
            logger.warning("WiFi/API failure during boot.")
            lcd.write_lines("Error: WiFi", "Offline Mode")
            buzzer.error_alert()
            await asyncio.sleep(2)
    except Exception as e:
        logger.warning(f"API check failed: {e}")
        state.wifi_error = True
        lcd.write_lines("Error: WiFi", "Offline Mode")
        buzzer.error_alert()
        await asyncio.sleep(2)


async def run_web_server() -> None:
    """Starts the FastAPI Web Interface."""
    import uvicorn
    config = uvicorn.Config(app=app, host=settings.web_host, port=settings.web_port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


# --- 5. MAIN ENTRY POINT ---


async def main_async() -> None:
    """Main async entry point for the weather station application."""
    db: DatabaseManager | None = None
    lcd: WeatherLCD | None = None
    buzzer: WeatherBuzzer | None = None
    
    try:
        # Initialize Database
        db = DatabaseManager()
        await db.initialize()
        logger.info("Database initialized")

        # Initialize Hardware
        lcd = WeatherLCD()
        sensors = WeatherSensors()
        buzzer = WeatherBuzzer()

        # Initialize Services
        weather_service = WeatherService()
        bot = WeatherBot()

        # Run Diagnostics (Loading Screen)
        await run_diagnostics(lcd, sensors, buzzer, weather_service)

        logger.info("System Ready. Starting background tasks.")

        # Prepare the core tasks
        tasks = [
            weather_fetcher(weather_service),
            dht_reader(sensors),
            data_logger(db),
            DisplayManager(lcd).run_loop(),
            InputProcessor(sensors, buzzer).run_loop(),
            run_web_server()
        ]

        # Check for Discord token
        token = settings.discord_token or os.getenv("WEATHER_DISCORD_TOKEN")

        if token:
            logger.info("Discord token detected. Starting Discord Bot...")
            tasks.append(bot.start(token))
        else:
            logger.warning("Discord Token missing. Bot will not start.")

        # Run everything in parallel
        await asyncio.gather(*tasks)

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.critical(f"Startup failed: {e}", exc_info=True)
        print(f"CRITICAL STARTUP ERROR: {e}")
    finally:
        # Cleanup resources
        logger.info("Shutting down weather station...")
        if lcd:
            try:
                lcd.clear()
            except Exception:
                pass
        if buzzer:
            try:
                buzzer.active_buzzer.close()
                buzzer.passive_buzzer.close()
            except Exception:
                pass


def main_entry() -> None:
    """Console script entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nShutting down station...")
        sys.exit(0)


# --- 6. DIRECT EXECUTION ---
if __name__ == "__main__":
    main_entry()
