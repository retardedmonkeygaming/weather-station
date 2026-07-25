from gpiozero import Buzzer
from hardware.pins import BUZZER_PIN

def get_buzzer() -> Buzzer:
    return Buzzer(BUZZER_PIN)