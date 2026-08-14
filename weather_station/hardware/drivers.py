"""
Hardware Abstraction Layer
Provides mock and real implementations for all hardware components.
Allows development without physical hardware.
"""

import asyncio
import random
from datetime import datetime
from typing import Optional, Tuple, List
from abc import ABC, abstractmethod


class MockMode:
    """Configuration for mock hardware behavior"""
    ENABLED = True
    SIMULATE_SENSOR_ERRORS = False
    ERROR_CHANCE = 0.05  # 5% chance of error when simulating


class BaseSensor(ABC):
    """Abstract base class for all sensors"""
    
    @abstractmethod
    async def read(self) -> dict:
        """Read sensor data and return as dictionary"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the sensor, return success status"""
        pass


class MockDHTSensor(BaseSensor):
    """Mock DHT11/DHT22 sensor for development"""
    
    def __init__(self, pin: int = 4):
        self.pin = pin
        self._initialized = False
        self._base_temp = 24.0
        self._base_humidity = 45.0
    
    async def initialize(self) -> bool:
        await asyncio.sleep(0.1)  # Simulate init delay
        self._initialized = True
        return True
    
    async def read(self) -> dict:
        if not self._initialized:
            return {"temperature": None, "humidity": None, "error": "Not initialized"}
        
        # Simulate realistic fluctuations
        if MockMode.SIMULATE_SENSOR_ERRORS and random.random() < MockMode.ERROR_CHANCE:
            return {"temperature": None, "humidity": None, "error": "Read timeout"}
        
        # Add small random variations
        temp_variation = random.uniform(-0.3, 0.3)
        humidity_variation = random.uniform(-2, 2)
        
        temperature = round(self._base_temp + temp_variation, 1)
        humidity = round(min(100, max(0, self._base_humidity + humidity_variation)), 1)
        
        # Slowly drift base values to simulate day/night changes
        hour = datetime.now().hour
        self._base_temp = 24.0 + 3.0 * math.sin((hour - 6) * math.pi / 12)
        
        return {"temperature": temperature, "humidity": humidity, "error": None}


class MockButton:
    """Mock button/touch sensor"""
    
    def __init__(self, pin: int = 27):
        self.pin = pin
        self._pressed = False
        self._callbacks = []
    
    @property
    def is_pressed(self) -> bool:
        return self._pressed
    
    def register_callback(self, callback):
        self._callbacks.append(callback)
    
    def simulate_press(self, duration: float = 0.3):
        """Simulate a button press for testing"""
        self._pressed = True
        asyncio.get_event_loop().call_later(duration, self._release)
    
    def _release(self):
        self._pressed = False


class MockBuzzer:
    """Mock buzzer for audio feedback"""
    
    def __init__(self, pin: int = 2):
        self.pin = pin
        self._on = False
    
    @property
    def is_on(self) -> bool:
        return self._on
    
    def on(self):
        self._on = True
        print(f"[BUZZER] ON")
    
    def off(self):
        self._on = False
        print(f"[BUZZER] OFF")
    
    async def beep(self, duration: float = 0.1, repeats: int = 1, pause: float = 0.05):
        """Simulate a beep pattern"""
        for i in range(repeats):
            self.on()
            await asyncio.sleep(duration)
            self.off()
            if i < repeats - 1:
                await asyncio.sleep(pause)


class MockLCD:
    """Mock 16x2 LCD display"""
    
    def __init__(self, rs: int = 22, en: int = 17, d4: int = 25, 
                 d5: int = 24, d6: int = 23, d7: int = 18):
        self.pins = {"rs": rs, "en": en, "d4": d4, "d5": d5, "d6": d6, "d7": d7}
        self._message = ""
        self._backlight = True
        self._custom_chars = {}
    
    @property
    def message(self) -> str:
        return self._message
    
    @message.setter
    def message(self, value: str):
        self._message = value
        print(f"[LCD] {value}")
    
    def clear(self):
        self._message = ""
        print("[LCD] CLEARED")
    
    def create_char(self, slot: int, bitmap: List[int]):
        """Define a custom character"""
        if 0 <= slot <= 7:
            self._custom_chars[slot] = bitmap
            print(f"[LCD] Custom char {slot} defined")
    
    def set_backlight(self, state: bool):
        self._backlight = state
        print(f"[LCD] Backlight: {'ON' if state else 'OFF'}")


class RealDHTSensor(BaseSensor):
    """Real DHT sensor using adafruit_dht"""
    
    def __init__(self, pin: int = 4, sensor_type: str = "DHT11"):
        self.pin = pin
        self.sensor_type = sensor_type
        self._device = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        try:
            import board
            import adafruit_dht
            
            if self.sensor_type == "DHT11":
                self._device = adafruit_dht.DHT11(board.D4, use_pulseio=False)
            else:
                self._device = adafruit_dht.DHT22(board.D4, use_pulseio=False)
            
            await asyncio.sleep(0.5)
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize DHT sensor: {e}")
            return False
    
    async def read(self) -> dict:
        if not self._initialized or self._device is None:
            return {"temperature": None, "humidity": None, "error": "Not initialized"}
        
        try:
            loop = asyncio.get_running_loop()
            temperature = await loop.run_in_executor(None, lambda: self._device.temperature)
            humidity = await loop.run_in_executor(None, lambda: self._device.humidity)
            
            if temperature is None or humidity is None:
                return {"temperature": None, "humidity": None, "error": "Invalid reading"}
            
            return {"temperature": float(temperature), "humidity": float(humidity), "error": None}
        except Exception as e:
            return {"temperature": None, "humidity": None, "error": str(e)}


class RealButton:
    """Real button using gpiozero"""
    
    def __init__(self, pin: int = 27):
        from gpiozero import Button
        self._button = Button(pin, pull_up=False, bounce_time=0.08)
    
    @property
    def is_pressed(self) -> bool:
        return self._button.is_pressed
    
    def register_callback(self, callback):
        self._button.when_pressed = callback


class RealBuzzer:
    """Real buzzer using gpiozero"""
    
    def __init__(self, pin: int = 2):
        from gpiozero import Buzzer
        self._buzzer = Buzzer(pin)
    
    @property
    def is_on(self) -> bool:
        return self._buzzer.value
    
    def on(self):
        self._buzzer.on()
    
    def off(self):
        self._buzzer.off()
    
    async def beep(self, duration: float = 0.1, repeats: int = 1, pause: float = 0.05):
        for i in range(repeats):
            self.on()
            await asyncio.sleep(duration)
            self.off()
            if i < repeats - 1:
                await asyncio.sleep(pause)


class RealLCD:
    """Real LCD using adafruit_character_lcd"""
    
    def __init__(self, rs: int = 22, en: int = 17, d4: int = 25,
                 d5: int = 24, d6: int = 23, d7: int = 18):
        import board
        import digitalio
        import adafruit_character_lcd.character_lcd as character_lcd
        
        self._rs = digitalio.DigitalInOut(getattr(board, f"D{rs}"))
        self._en = digitalio.DigitalInOut(getattr(board, f"D{en}"))
        self._d4 = digitalio.DigitalInOut(getattr(board, f"D{d4}"))
        self._d5 = digitalio.DigitalInOut(getattr(board, f"D{d5}"))
        self._d6 = digitalio.DigitalInOut(getattr(board, f"D{d6}"))
        self._d7 = digitalio.DigitalInOut(getattr(board, f"D{d7}"))
        
        self._lcd = character_lcd.Character_LCD_Mono(
            self._rs, self._en, self._d4, self._d5, self._d6, self._d7,
            columns=16, rows=2
        )
    
    @property
    def message(self) -> str:
        return self._lcd.message
    
    @message.setter
    def message(self, value: str):
        self._lcd.message = value
    
    def clear(self):
        self._lcd.clear()
    
    def create_char(self, slot: int, bitmap: List[int]):
        self._lcd.create_char(slot, bitmap)
    
    def set_backlight(self, state: bool):
        self._lcd.backlight = state


def create_hardware(mock: bool = True) -> dict:
    """
    Factory function to create hardware instances.
    
    Args:
        mock: If True, use mock hardware; otherwise use real hardware
    
    Returns:
        Dictionary with hardware instances
    """
    if mock:
        return {
            "dht_sensor": MockDHTSensor(),
            "button": MockButton(),
            "buzzer": MockBuzzer(),
            "lcd": MockLCD()
        }
    else:
        return {
            "dht_sensor": RealDHTSensor(),
            "button": RealButton(),
            "buzzer": RealBuzzer(),
            "lcd": RealLCD()
        }


# Import math for mock sensor calculations
import math
