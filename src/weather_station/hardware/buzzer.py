import time
from gpiozero import Buzzer
from weather_station.hardware.pins import BUZZER_PIN

class WeatherBuzzer:
    def __init__(self):
        # We use gpiozero for easy buzzer management
        try:
            self.buzzer = Buzzer(BUZZER_PIN)
        except Exception:
            self.buzzer = None
            print("Warning: Buzzer hardware not initialized.")

    def beep(self, duration=0.1, repeats=1):
        """Standard beep for feedback."""
        if not self.buzzer: return
        for _ in range(repeats):
            self.buzzer.on()
            time.sleep(duration)
            self.buzzer.off()
            if repeats > 1:
                time.sleep(0.05)

    def error_alert(self):
        """Rapid triple beep for system errors."""
        if not self.buzzer: return
        for _ in range(3):
            self.buzzer.on()
            time.sleep(0.05)
            self.buzzer.off()
            time.sleep(0.05)

    def tick(self):
        """A very short pulse for tactile touch feedback."""
        if not self.buzzer: return
        self.buzzer.on()
        time.sleep(0.01)
        self.buzzer.off()