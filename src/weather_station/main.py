import asyncio
import logging
import uvicorn
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.utils.logging_setup import setup_logging
from weather_station.persistence.database import DatabaseManager
from weather_station.hardware import WeatherLCD, WeatherSensors, WeatherBuzzer
from weather_station.services import WeatherService, SystemService
from weather_station.display.manager import DisplayManager
from weather_station.input.processor import InputProcessor
from weather_station.web.app import app

async def weather_fetcher(service):
    while True:
        await service.fetch_all()
        await asyncio.sleep(settings.api_rate * 60)

async def run_web_server():
    """Runs Uvicorn in an async-friendly way."""
    config = uvicorn.Config(
        app=app, 
        host=settings.web_host, 
        port=settings.web_port, 
        log_level="error"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def run_diagnostics(lcd, sensors, buzzer, weather_service):
    """Restores your original on-boot diagnostics and loading screen."""
    lcd.clear()
    lcd.write_lines(" WEATHER STATION", " v3.0 Booting...")
    buzzer.beep(0.06, repeats=2)
    await asyncio.sleep(1.2)

    # Loading Animation
    lcd.clear()
    for i in range(16):
        lcd.write_lines("Loading System..", "\x06" * (i + 1))
        await asyncio.sleep(0.08)

    # Hardware Check
    temp, _ = sensors.read_dht()
    if temp is None:
        state.dht_error = True
        lcd.write_lines("Error: DHT11", "Sensor Missing")
        buzzer.error_alert()
        await asyncio.sleep(2)

    # WiFi Check
    await weather_service.fetch_all()
    if state.wifi_error:
        lcd.write_lines("Error: WiFi", "Not Connected")
        buzzer.error_alert()
        await asyncio.sleep(2)

async def main():
    setup_logging()
    db = DatabaseManager()
    await db.initialize()
    
    lcd = WeatherLCD()
    sensors = WeatherSensors()
    buzzer = WeatherBuzzer()
    weather_service = WeatherService()
    
    # RUN DIAGNOSTICS FIRST
    await run_diagnostics(lcd, sensors, buzzer, weather_service)

    logger.info("Starting Weather Station Modules...")
    await asyncio.gather(
        weather_fetcher(weather_service),
        dht_reader(sensors),
        DisplayManager(lcd).run_loop(),
        InputProcessor(sensors, buzzer).run_loop(),
        run_web_server()
    )