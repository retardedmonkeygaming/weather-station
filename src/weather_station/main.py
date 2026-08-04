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

async def main():
    setup_logging()
    logger = logging.getLogger("Main")

    # Initialize Hardware & DB
    db = DatabaseManager()
    await db.initialize()
    
    # Initialize Hardware
    lcd = WeatherLCD()
    sensors = WeatherSensors()
    buzzer = WeatherBuzzer()

    # Initialize Services
    weather_service = WeatherService()
    display_manager = DisplayManager(lcd)
    input_processor = InputProcessor(sensors, buzzer)

    logger.info("Starting Weather Station Modules...")

    # We use gather to run all background tasks AND the web server together
    try:
        await asyncio.gather(
            weather_fetcher(weather_service),
            dht_reader(sensors),
            display_manager.run_loop(),
            input_processor.run_loop(),
            run_web_server()
        )
    except Exception as e:
        logger.error(f"Critical System Failure: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass