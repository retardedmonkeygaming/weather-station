import aiohttp
import logging
from weather_station.core.config import settings
from weather_station.core.state import state

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.weather_url = "https://api.open-meteo.com/v1/forecast"
        self.aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def _get_weather_info(self, code):
        if code in [0, 1]: return "\x05", "Clear"
        if code in [2, 3]: return "\x04", "Cloudy"
        if code in [45, 48]: return "\x04", "Foggy"
        if code in [51, 53, 55, 61, 63, 65]: return "\x04", "Rain"
        if code in [71, 73, 75]: return "\x04", "Snow"
        if code in [95, 96, 99]: return "\x04", "Storm"
        return "\x05", "Clear"

    async def fetch_all(self):
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
                async with session.get(self.weather_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        state.outdoor_temp = f"{data['current']['temperature_2m']:.1f}"
                        state.outdoor_max = f"{data['daily']['temperature_2m_max'][0]:.1f}"
                        state.outdoor_min = f"{data['daily']['temperature_2m_min'][0]:.1f}"
                        state.outdoor_humid = f"{data['current']['relative_humidity_2m']}"
                        state.uv_index = f"{data['current']['uv_index']:.1f}"
                        state.uv_max = f"{data['daily']['uv_index_max'][0]:.1f}"
                        state.weather_icon, state.weather_text = self._get_weather_info(data['current']['weather_code'])
                        state.wifi_error = False
                    else: state.wifi_error = True

                async with session.get(self.aqi_url, params=aqi_params) as resp:
                    if resp.status == 200:
                        aqi_data = await resp.json()
                        state.aqi_val = str(int(aqi_data['current']['us_aqi']))
                        state.pm2_5 = str(int(aqi_data['current']['pm2_5']))
                        state.pm10 = str(int(aqi_data['current']['pm10']))
            except Exception as e:
                logger.error(f"Weather API Error: {e}")
                state.wifi_error = True