import asyncio
import logging
import sys
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# --- 1. ULTIMATE ENV LOAD (MUST BE TOP) ---
# This looks for .env in /vxprxx/weather-station/ regardless of where you start
current_dir = Path(__file__).resolve().parent # weather_station/
src_dir = current_dir.parent                  # src/
root_dir = src_dir.parent                     # weather-station/
env_path = root_dir / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"DEBUG: .env found at {env_path}")
else:
    print(f"DEBUG: .env NOT FOUND at {env_path}")

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

# --- 4. BACKGROUND WORKER DEFINITIONS ---

async def weather_fetcher(service):
    """Periodically fetches data from Open-Meteo."""
    while True:
        await service.fetch_all()
        await asyncio.sleep(settings.api_rate * 60)

async def dht_reader(sensors):
    """Periodically reads the local DHT11 sensor."""
    while True:
        temp, humid = sensors.read_dht()
        if temp is not None:
            state.indoor_temp_raw = temp
            state.indoor_temp = temp + settings.dht_temp_offset
            state.indoor_humid = humid
            state.dht_error = False
        else:
            state.dht_error = True
        await asyncio.sleep(3)

async def run_diagnostics(lcd, sensors, buzzer, weather):
    """Literal boot sequence logic."""
    print("Running Diagnostics...")
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
    await weather.fetch_all()
    if state.wifi_error:
        logger.warning("WiFi/API failure during boot.")
        lcd.write_lines("Error: WiFi", "Offline Mode")
        buzzer.error_alert()
        await asyncio.sleep(2)

async def run_web_server():
    """Starts the FastAPI Web Interface."""
    config = uvicorn.Config(app=app, host=settings.web_host, port=settings.web_port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

# --- 5. THE SINGLE MAIN FUNCTION ---

async def main():
    try:
        # Initialize Database
        db = DatabaseManager()
        await db.initialize()
        
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
            DisplayManager(lcd).run_loop(),
            InputProcessor(sensors, buzzer).run_loop(),
            run_web_server()
        ]

        # Check for token in .env (via os.getenv)
        token = os.getenv("WEATHER_DISCORD_TOKEN")
        
        if token:
            logger.info("Token detected. Starting Discord Bot...")
            tasks.append(bot.start(token))
        else:
            logger.warning("Discord Token missing in .env. Bot will not start.")

        # Run everything in parallel
        await asyncio.gather(*tasks)

    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}")
        logger.critical(f"Startup failed: {e}")

# --- 6. ENTRY POINT ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down station...")
        sys.exit(0)