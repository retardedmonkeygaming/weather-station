import board
import adafruit_dht
from gpiozero import Button
from weather_station.hardware.pins import DHT_PIN, TOUCH_PIN

class WeatherSensors:
    def __init__(self):
        # DHT11 setup
        self.dht = adafruit_dht.DHT11(
            getattr(board, f"D{DHT_PIN}"), 
            use_pulseio=False
        )
        # Button setup (Touch sensor behaves like a button)
        self.button = Button(TOUCH_PIN, pull_up=False, bounce_time=0.08)

    def read_dht(self):
        """Returns (temp, humidity) or (None, None) on failure."""
        try:
            return self.dht.temperature, self.dht.humidity
        except Exception:
            return None, None

    def is_pressed(self):
        return self.button.is_pressed