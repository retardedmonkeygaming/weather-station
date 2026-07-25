"""DHT11 Temperature & Humidity Sensor Interface."""
import board
import adafruit_dht
from hardware.pins import DHT_PIN

class DHTSensor:
    def __init__(self):
        pin_attr = getattr(board, f"D{DHT_PIN}")
        self._sensor = adafruit_dht.DHT11(pin_attr)

    def read(self):
        temp = self._sensor.temperature
        humid = self._sensor.humidity
        if temp is None or humid is None:
            raise RuntimeError("DHT sensor returned None value")
        return temp, humid

    def exit(self):
        self._sensor.exit()