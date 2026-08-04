import asyncio
import logging
import sys
import uvicorn
import os # Added for environment variables
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

setup_logging()
logger = logging.getLogger("Main")

async def weather_fetcher(service):
    while True:
        await service.fetch_all()
        await asyncio.sleep(settings.api_rate * 60)

async def dht_reader(sensors):
    while True:
        temp, humid = sensors.read_dht()
        if temp is not None:
            state.indoor_temp = temp + settings.dht_temp_offset
            state.indoor_humid = humid
            state.dht_error = False
        else:
            state.dht_error = True
        await asyncio.sleep(3)

async def run_diagnostics(lcd, sensors, buzzer, weather):
    print("Running Diagnostics...")
    lcd.clear()
    lcd.write_lines(" WEATHER STATION", " v3.0 Booting...")
    buzzer.beep(0.06, repeats=2)
    await asyncio.sleep(1.2)

    lcd.clear()
    for i in range(16):
        lcd.write_lines("Loading System..", "\x06" * (i + 1))
        await asyncio.sleep(0.08)

    temp, _ = sensors.read_dht()
    if temp is None:
        logger.warning("DHT11 not detected during boot.")
        lcd.write_lines("Error: DHT11", "Check Sensor")
        buzzer.error_alert()
        await asyncio.sleep(2)

    await weather.fetch_all()
    if state.wifi_error:
        logger.warning("WiFi/API failure during boot.")
        lcd.write_lines("Error: WiFi", "Offline Mode")
        buzzer.error_alert()
        await asyncio.sleep(2)

async def run_web_server():
    config = uvicorn.Config(app=app, host=settings.web_host, port=settings.web_port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    try:
        db = DatabaseManager()
        await db.initialize()
        
        lcd = WeatherLCD()
        sensors = WeatherSensors()
        buzzer = WeatherBuzzer()
        weather_service = WeatherService()
        bot = WeatherBot() 
        
        await run_diagnostics(lcd, sensors, buzzer, weather_service)

        logger.info("System Ready. Starting background tasks.")

        # Gather all tasks including the Discord Bot
        tasks = [
            weather_fetcher(weather_service),
            dht_reader(sensors),
            DisplayManager(lcd).run_loop(),
            InputProcessor(sensors, buzzer).run_loop(),
            run_web_server()
        ]

        # Only start the bot if you have put your token in config or .env
        if settings.discord_token:
            tasks.append(bot.start(settings.discord_token))
        else:
            logger.warning("Discord Token missing. Bot not starting.")

        await asyncio.gather(*tasks)

    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}")
        logger.critical(f"Startup failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())

# ... other imports ...
import os
from weather_station.services.discord_bot import WeatherBot

async def main():
    try:
        db = DatabaseManager()
        await db.initialize()
        
        lcd = WeatherLCD()
        sensors = WeatherSensors()
        buzzer = WeatherBuzzer()
        weather_service = WeatherService()
        
        # Initialize the Bot instance
        bot = WeatherBot()
        
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

        # Add the Bot task ONLY if a token exists
        token = os.getenv("WEATHER_DISCORD_TOKEN")
        if token:
            tasks.append(bot.start(token))
        else:
            logger.warning("Discord Token missing. Bot will not start.")

        # Run everything in parallel
        await asyncio.gather(*tasks)

    except Exception as e:
        logger.critical(f"Startup failed: {e}")