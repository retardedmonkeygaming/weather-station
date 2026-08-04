import aiohttp
import logging
from weather_station.core.config import settings
from weather_station.core.state import state

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.weather_url = "https://api.open-meteo.com/v1/forecast"
        self.aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    async def fetch_all(self):
        """Fetches both Weather and AQI data in parallel."""
        params = {
            "latitude": settings.latitude,
            "longitude": settings.longitude,
            "current": "temperature_2m,relative_humidity_2m,weather_code,uv_index",
            "daily": "temperature_2m_max,temperature_2m_min,uv_index_max",
            "timezone": "auto"
        }
        aqi_params = {
            "latitude": settings.latitude,
            "longitude": settings.longitude,
            "current": "us_aqi,pm10,pm2_5"
        }

        async with aiohttp.ClientSession() as session:
            try:
                # Fetch Weather
                async with session.get(self.weather_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        state.outdoor_temp = f"{data['current']['temperature_2m']:.1f}"
                        state.outdoor_humid = f"{data['current']['relative_humidity_2m']}"
                        # ... other data points mapping to state ...
                        state.wifi_error = False
                    else:
                        state.wifi_error = True

                # Fetch AQI
                async with session.get(self.aqi_url, params=aqi_params) as resp:
                    if resp.status == 200:
                        aqi_data = await resp.json()
                        state.aqi_val = str(int(aqi_data['current']['us_aqi']))
                        # ... mapping AQI status ...
            
            except Exception as e:
                logger.error(f"Failed to fetch outdoor weather: {e}")
                state.wifi_error = True