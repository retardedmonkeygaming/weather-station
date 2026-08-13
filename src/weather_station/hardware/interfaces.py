"""
Hardware Abstraction Layer (HAL)
Defines interfaces for all hardware components with real and mock implementations
Central pin mapping configuration
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import random


class HardwareInterface(ABC):
    """Base interface for all hardware components"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize hardware, return True if successful"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Clean shutdown of hardware"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if hardware is available/connected"""
        pass


class LCDInterface(HardwareInterface):
    """LCD display interface"""
    
    @abstractmethod
    async def display_text(self, row: int, col: int, text: str) -> None:
        """Display text at specific position"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear display"""
        pass
    
    @abstractmethod
    async def set_backlight(self, on: bool) -> None:
        """Control backlight"""
        pass
    
    @abstractmethod
    async def create_custom_char(self, char_code: int, bitmap: List[int]) -> None:
        """Create custom character"""
        pass


class TouchInterface(HardwareInterface):
    """Touch sensor interface"""
    
    @abstractmethod
    async def read_touch(self) -> bool:
        """Read touch state, return True if touched"""
        pass


class BuzzerInterface(HardwareInterface):
    """Buzzer interface"""
    
    @abstractmethod
    async def beep(self, duration: float = 0.1, frequency: int = 1000) -> None:
        """Play a beep sound"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop buzzer"""
        pass


class SensorInterface(HardwareInterface):
    """Environmental sensor interface"""
    
    @abstractmethod
    async def read_temperature(self) -> Optional[float]:
        """Read temperature in Celsius"""
        pass
    
    @abstractmethod
    async def read_humidity(self) -> Optional[float]:
        """Read humidity percentage"""
        pass
    
    @abstractmethod
    async def read_pressure(self) -> Optional[float]:
        """Read pressure in hPa"""
        pass


# Central Pin Mapping Configuration
PIN_MAPPING = {
    'lcd': {
        'i2c_bus': 1,
        'i2c_address': 0x27,
        'columns': 16,
        'rows': 2,
    },
    'touch': {
        'gpio_pin': 4,
    },
    'buzzer': {
        'gpio_pin': 17,
    },
    'backlight': {
        'gpio_pin': 5,
    },
    'sensors': {
        'temperature': 'DS18B20',  # or 'DHT22', 'BME280'
        'humidity': 'DHT22',
        'pressure': 'BME280',
    }
}


class MockHardware(LCDInterface, TouchInterface, BuzzerInterface, SensorInterface):
    """
    Complete mock implementation for PC development and testing.
    Simulates all hardware components without physical devices.
    """
    
    def __init__(self):
        self._initialized = False
        self._display_buffer = ["", ""]  # 2 rows
        self._backlight_on = True
        self._touch_state = False
        self._buzzer_active = False
        self._custom_chars: Dict[int, List[int]] = {}
        
        # Simulated sensor values
        self._sim_temp = 22.5
        self._sim_humidity = 45.0
        self._sim_pressure = 1013.25
        
    async def initialize(self) -> bool:
        self._initialized = True
        print("[MockHardware] Initialized successfully")
        return True
    
    async def shutdown(self) -> None:
        self._initialized = False
        print("[MockHardware] Shutdown complete")
    
    async def is_available(self) -> bool:
        return self._initialized
    
    # LCD Implementation
    async def display_text(self, row: int, col: int, text: str) -> None:
        if not self._initialized:
            return
        if 0 <= row < 2:
            padded = text.ljust(16)[:16]
            self._display_buffer[row] = padded
            print(f"[MockLCD] Row {row}: {padded}")
    
    async def clear(self) -> None:
        self._display_buffer = ["", ""]
        print("[MockLCD] Cleared")
    
    async def set_backlight(self, on: bool) -> None:
        self._backlight_on = on
        print(f"[MockLCD] Backlight: {'ON' if on else 'OFF'}")
    
    async def create_custom_char(self, char_code: int, bitmap: List[int]) -> None:
        self._custom_chars[char_code] = bitmap
        print(f"[MockLCD] Custom char {char_code} created")
    
    # Touch Implementation
    async def read_touch(self) -> bool:
        # Simulate occasional touches for testing
        if not self._initialized:
            return False
        # Random touch simulation (1% chance)
        self._touch_state = random.random() < 0.01
        return self._touch_state
    
    # Buzzer Implementation
    async def beep(self, duration: float = 0.1, frequency: int = 1000) -> None:
        self._buzzer_active = True
        print(f"[MockBuzzer] Beep: {duration}s @ {frequency}Hz")
        # In real implementation, would wait for duration
        self._buzzer_active = False
    
    async def stop(self) -> None:
        self._buzzer_active = False
        print("[MockBuzzer] Stopped")
    
    # Sensor Implementation
    async def read_temperature(self) -> Optional[float]:
        if not self._initialized:
            return None
        # Simulate realistic temperature variations
        self._sim_temp += random.uniform(-0.2, 0.2)
        self._sim_temp = max(-10, min(45, self._sim_temp))  # Clamp to realistic range
        return round(self._sim_temp, 1)
    
    async def read_humidity(self) -> Optional[float]:
        if not self._initialized:
            return None
        self._sim_humidity += random.uniform(-1, 1)
        self._sim_humidity = max(10, min(95, self._sim_humidity))
        return round(self._sim_humidity, 1)
    
    async def read_pressure(self) -> Optional[float]:
        if not self._initialized:
            return None
        self._sim_pressure += random.uniform(-0.5, 0.5)
        return round(self._sim_pressure, 2)
    
    # Helper for testing
    def set_simulated_touch(self, state: bool) -> None:
        """Manually set touch state for testing"""
        self._touch_state = state
    
    def get_display_content(self) -> Tuple[str, str]:
        """Get current display content for testing"""
        return tuple(self._display_buffer)


class RealHardware(LCDInterface, TouchInterface, BuzzerInterface, SensorInterface):
    """
    Real hardware implementation for Raspberry Pi.
    Uses actual GPIO pins and I2C communication.
    """
    
    def __init__(self, pin_mapping: Optional[Dict] = None):
        self.pin_mapping = pin_mapping or PIN_MAPPING
        self._initialized = False
        self._lcd = None
        self._gpio = None
        self._sensor = None
        
    async def initialize(self) -> bool:
        try:
            # Import hardware libraries only when needed
            # This allows the code to run on PC with mock hardware
            
            # LCD (I2C)
            try:
                from RPLCD.i2c import CharLCD as RealLCD
                self._lcd = RealLCD(
                    port=self.pin_mapping['lcd']['i2c_bus'],
                    address=self.pin_mapping['lcd']['i2c_address'],
                    cols=self.pin_mapping['lcd']['columns'],
                    rows=self.pin_mapping['lcd']['rows'],
                    dotsize=8
                )
                print("[RealHardware] LCD initialized")
            except ImportError:
                print("[RealHardware] RPLCD not available, using mock LCD")
                return False
            
            # GPIO for touch and buzzer
            try:
                import RPi.GPIO as GPIO
                self._gpio = GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Setup touch pin
                touch_pin = self.pin_mapping['touch']['gpio_pin']
                GPIO.setup(touch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                # Setup buzzer pin
                buzzer_pin = self.pin_mapping['buzzer']['gpio_pin']
                GPIO.setup(buzzer_pin, GPIO.OUT)
                GPIO.output(buzzer_pin, GPIO.LOW)
                
                # Setup backlight pin
                backlight_pin = self.pin_mapping['backlight']['gpio_pin']
                GPIO.setup(backlight_pin, GPIO.OUT)
                GPIO.output(backlight_pin, GPIO.HIGH)
                
                print("[RealHardware] GPIO initialized")
            except ImportError:
                print("[RealHardware] RPi.GPIO not available")
                return False
            
            # Temperature/Humidity sensor
            try:
                from w1thermsensor import W1ThermSensor
                self._temp_sensor = W1ThermSensor()
                print("[RealHardware] Temperature sensor initialized")
            except ImportError:
                print("[RealHardware] w1thermsensor not available")
                self._temp_sensor = None
            
            self._initialized = True
            print("[RealHardware] All hardware initialized successfully")
            return True
            
        except Exception as e:
            print(f"[RealHardware] Initialization failed: {e}")
            return False
    
    async def shutdown(self) -> None:
        try:
            if self._gpio:
                self._gpio.cleanup()
            if self._lcd:
                self._lcd.clear()
                self._lcd.backlight_off()
            self._initialized = False
            print("[RealHardware] Shutdown complete")
        except Exception as e:
            print(f"[RealHardware] Shutdown error: {e}")
    
    async def is_available(self) -> bool:
        return self._initialized and self._lcd is not None
    
    # LCD Implementation
    async def display_text(self, row: int, col: int, text: str) -> None:
        if not self._initialized or not self._lcd:
            return
        try:
            self._lcd.cursor_pos = (row, col)
            self._lcd.write_string(text)
        except Exception as e:
            print(f"[RealLCD] Display error: {e}")
    
    async def clear(self) -> None:
        if self._lcd:
            self._lcd.clear()
    
    async def set_backlight(self, on: bool) -> None:
        if self._lcd:
            if on:
                self._lcd.backlight_on()
            else:
                self._lcd.backlight_off()
    
    async def create_custom_char(self, char_code: int, bitmap: List[int]) -> None:
        if self._lcd:
            try:
                self._lcd.create_char(char_code, bitmap)
            except Exception as e:
                print(f"[RealLCD] Custom char error: {e}")
    
    # Touch Implementation
    async def read_touch(self) -> bool:
        if not self._initialized or not self._gpio:
            return False
        try:
            touch_pin = self.pin_mapping['touch']['gpio_pin']
            return self._gpio.input(touch_pin) == GPIO.LOW
        except Exception as e:
            print(f"[RealTouch] Read error: {e}")
            return False
    
    # Buzzer Implementation
    async def beep(self, duration: float = 0.1, frequency: int = 1000) -> None:
        if not self._initialized or not self._gpio:
            return
        try:
            import time
            buzzer_pin = self.pin_mapping['buzzer']['gpio_pin']
            
            # Simple beep (frequency control requires PWM)
            self._gpio.output(buzzer_pin, GPIO.HIGH)
            time.sleep(duration)
            self._gpio.output(buzzer_pin, GPIO.LOW)
        except Exception as e:
            print(f"[RealBuzzer] Beep error: {e}")
    
    async def stop(self) -> None:
        if self._gpio:
            buzzer_pin = self.pin_mapping['buzzer']['gpio_pin']
            self._gpio.output(buzzer_pin, GPIO.LOW)
    
    # Sensor Implementation
    async def read_temperature(self) -> Optional[float]:
        if not self._temp_sensor:
            return None
        try:
            return round(self._temp_sensor.get_temperature(), 1)
        except Exception as e:
            print(f"[RealSensor] Temperature read error: {e}")
            return None
    
    async def read_humidity(self) -> Optional[float]:
        # Would need DHT22 or BME280 for humidity
        print("[RealSensor] Humidity sensor not configured")
        return None
    
    async def read_pressure(self) -> Optional[float]:
        # Would need BME280 for pressure
        print("[RealSensor] Pressure sensor not configured")
        return None
