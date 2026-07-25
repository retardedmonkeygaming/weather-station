# weather_station/hardware/touch.py
from gpiozero import Button
from weather_station.hardware.pins import TOUCH_PIN

def get_touch_button() -> Button:
    return Button(TOUCH_PIN, pull_up=False)

# weather_station/hardware/buzzer.py
from gpiozero import Buzzer
from weather_station.hardware.pins import BUZZER_PIN

def get_buzzer() -> Buzzer:
    return Buzzer(BUZZER_PIN)