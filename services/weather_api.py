"""Open-Meteo API Integration for Outdoor Weather & AQI."""
import aiohttp
import logging

logger = logging.getLogger("weather_station.services")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
AQI_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

async def fetch_weather_and_aqi(lat: float, lon: float) -> dict:
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "uv_index_max"],
        "timezone": "auto"
    }
    
    aqi_params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["us_aqi", "pm10", "pm2_5"],
        "timezone": "auto"
    }

    results = {}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(OPEN_METEO_URL, params=weather_params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    curr = data.get("current", {})
                    daily = data.get("daily", {})
                    results.update({
                        "outdoor_temp": curr.get("temperature_2m"),
                        "outdoor_humid": curr.get("relative_humidity_2m"),
                        "outdoor_min": daily.get("temperature_2m_min", [None])[0],
                        "outdoor_max": daily.get("temperature_2m_max", [None])[0],
                        "uv_current": daily.get("uv_index_max", [None])[0],
                    })
        except Exception as e:
            logger.error(f"Weather API fetch failed: {e}")

        try:
            async with session.get(AQI_URL, params=aqi_params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    curr = data.get("current", {})
                    us_aqi = curr.get("us_aqi")
                    
                    status = "Unknown"
                    if us_aqi is not None:
                        if us_aqi <= 50: status = "Good"
                        elif us_aqi <= 100: status = "Moderate"
                        elif us_aqi <= 150: status = "Unhealthy (SG)"
                        else: status = "Unhealthy"

                    results.update({
                        "aqi_val": str(us_aqi) if us_aqi is not None else "N/A",
                        "aqi_status": status,
                        "pm2_5_val": str(curr.get("pm2_5", "N/A")),
                        "pm10_val": str(curr.get("pm10", "N/A"))
                    })
        except Exception as e:
            logger.error(f"AQI API fetch failed: {e}")

    return results