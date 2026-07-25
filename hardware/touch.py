from gpiozero import Button
from hardware.pins import TOUCH_PIN

def get_touch_button() -> Button:
    return Button(TOUCH_PIN, pull_up=False)