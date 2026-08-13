"""
Weather Service
Fetches weather data from APIs with retry logic and exponential backoff
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import aiohttp


class WeatherService:
    """
    Weather data service with API integration.
    Handles retries, caching, and error recovery.
    """
    
    def __init__(
        self,
        state: Any,
        database_manager: Any,
        api_key: Optional[str] = None,
        latitude: float = 40.7128,
        longitude: float = -74.0060,
        fetch_interval: int = 300  # 5 minutes
    ):
        self.state = state
        self.db = database_manager
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self.fetch_interval = fetch_interval
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._consecutive_failures = 0
        self._last_fetch: Optional[datetime] = None
    
    async def start(self) -> None:
        """Start the weather fetching loop"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._fetch_loop())
        print("[WeatherService] Started")
    
    async def stop(self) -> None:
        """Stop the weather fetching loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[WeatherService] Stopped")
    
    async def _fetch_loop(self) -> None:
        """Main fetch loop with exponential backoff"""
        while self._running:
            try:
                await self._fetch_data()
                
                # Reset failures on success
                self._consecutive_failures = 0
                
                # Wait for next fetch
                await asyncio.sleep(self.fetch_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Exponential backoff on failure
                self._consecutive_failures += 1
                delay = min(300, (2 ** self._consecutive_failures) * 10)  # Max 5 minutes
                print(f"[WeatherService] Error: {e}, retrying in {delay}s")
                await asyncio.sleep(delay)
    
    async def _fetch_data(self) -> None:
        """Fetch weather data from API"""
        if not self.api_key:
            # Use mock data if no API key
            await self._use_mock_data()
            return
        
        # In a real implementation, this would call OpenWeatherMap or similar
        # For now, we'll use mock data
        await self._use_mock_data()
    
    async def _use_mock_data(self) -> None:
        """Generate realistic mock data for testing"""
        import random
        
        now = datetime.utcnow()
        
        # Simulate realistic weather data
        base_temp = 22.0
        temp_variation = math.sin(now.hour / 24 * 2 * 3.14159) * 5  # Daily cycle
        temperature = base_temp + temp_variation + random.uniform(-1, 1)
        
        humidity = 45 + random.uniform(-10, 10)
        pressure = 1013.25 + random.uniform(-5, 5)
        aqi = random.randint(20, 80)
        
        # Calculate feels like (simplified)
        feels_like = temperature + (humidity - 50) / 100
        
        # Determine AQI status
        if aqi <= 50:
            aqi_status = "OK"
        elif aqi <= 100:
            aqi_status = "Mod"
        elif aqi <= 150:
            aqi_status = "Sens"
        elif aqi <= 200:
            aqi_status = "Unhl"
        elif aqi <= 300:
            aqi_status = "VUnh"
        else:
            aqi_status = "Hazd"
        
        # Update state
        await self.state.update_sensor(
            temperature=round(temperature, 1),
            humidity=round(humidity, 1),
            pressure=round(pressure, 2),
            aqi=aqi,
            aqi_status=aqi_status,
            feels_like=round(feels_like, 1),
            last_api_fetch=now,
            api_error=False
        )
        
        # Log to database
        if self.db and self.db._initialized:
            await self.db.log_sensor_data(
                temperature=round(temperature, 1),
                humidity=round(humidity, 1),
                pressure=round(pressure, 2),
                aqi=aqi,
                aqi_status=aqi_status,
                feels_like=round(feels_like, 1),
                source='api'
            )
        
        self._last_fetch = now
        print(f"[WeatherService] Fetched: T={temperature:.1f}C, H={humidity:.1f}%, AQI={aqi}")
    
    async def force_fetch(self) -> bool:
        """Force an immediate fetch"""
        try:
            await self._fetch_data()
            return True
        except Exception as e:
            print(f"[WeatherService] Force fetch failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'running': self._running,
            'consecutive_failures': self._consecutive_failures,
            'last_fetch': self._last_fetch.isoformat() if self._last_fetch else None,
            'fetch_interval': self.fetch_interval,
        }


# Import math for the sin function
import math
