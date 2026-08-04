import time
from gpiozero import Buzzer as GPIOZeroBuzzer
from weather_station.hardware.pins import BUZZER_PIN

class WeatherBuzzer:
    def __init__(self):
        self.buzzer = GPIOZeroBuzzer(BUZZER_PIN)

    def beep(self, duration=0.1, repeats=1):
        for _ in range(repeats):
            self.buzzer.on()
            time.sleep(duration)
            self.buzzer.off()
            if repeats > 1:
                time.sleep(0.05)

    def error_alert(self):
        """Rapid triple beep for system errors."""
        self.beep(duration=0.05, repeats=3)

    def alarm_tone(self):
        """The tone used for the daily alarm."""
        self.buzzer.on()
        time.sleep(0.2)
        self.buzzer.off()