import time
from gpiozero import Buzzer, PWMOutputDevice
from weather_station.hardware.pins import ACTIVE_BUZZER_PIN, PASSIVE_BUZZER_PIN
from weather_station.core.config import settings

class WeatherBuzzer:
    def __init__(self):
        # Active buzzer: simple on/off beeps (GPIO 6)
        # Passive buzzer: tone generation via PWM (GPIO 16)
        try:
            self.active_buzzer = Buzzer(ACTIVE_BUZZER_PIN)
            self.passive_buzzer = PWMOutputDevice(PASSIVE_BUZZER_PIN, frequency=440)
        except Exception:
            self.active_buzzer = None
            self.passive_buzzer = None
            print("Warning: Buzzer hardware not initialized.")

    def _should_play(self):
        """Check if buzzer is enabled based on settings."""
        return settings.buzzer_mode != "MUTE"

    def beep(self, duration=0.1, repeats=1, use_active=True):
        """Standard beep for feedback. Uses active buzzer by default."""
        if not self._should_play():
            return
        if not self.active_buzzer:
            return
        for _ in range(repeats):
            self.active_buzzer.on()
            time.sleep(duration)
            self.active_buzzer.off()
            if repeats > 1:
                time.sleep(0.05)

    def tone(self, frequency=440, duration=0.1):
        """Play a tone on the passive buzzer at specified frequency."""
        if not self._should_play():
            return
        if not self.passive_buzzer:
            return
        self.passive_buzzer.frequency = frequency
        self.passive_buzzer.value = 0.5  # 50% duty cycle
        time.sleep(duration)
        self.passive_buzzer.value = 0

    def error_alert(self):
        """Rapid triple beep for system errors using active buzzer."""
        if not self._should_play():
            return
        if not self.active_buzzer:
            return
        for _ in range(3):
            self.active_buzzer.on()
            time.sleep(0.05)
            self.active_buzzer.off()
            time.sleep(0.05)

    def tick(self):
        """A very short pulse for tactile touch feedback using active buzzer."""
        if not self._should_play():
            return
        if not self.active_buzzer:
            return
        self.active_buzzer.on()
        time.sleep(0.01)
        self.active_buzzer.off()

    def melody(self, frequencies, note_duration=0.1):
        """Play a sequence of tones on the passive buzzer."""
        if not self._should_play():
            return
        if not self.passive_buzzer:
            return
        for freq in frequencies:
            self.tone(freq, note_duration)
            time.sleep(0.02)  # Small gap between notes