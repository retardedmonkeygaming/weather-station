"""Buzzer driver wrapper with global MUTE check."""
from gpiozero import Buzzer
from hardware.pins import BUZZER_PIN
from core.state import state


class StationBuzzer:
    def __init__(self):
        self._buzzer = Buzzer(BUZZER_PIN)

    def beep(self, on_time: float = 0.1, off_time: float = 0.1, n: int = 1):
        snap = state.get_snapshot_sync()
        # Respect global MUTE setting
        if snap.buzzer_mode == "MUTE":
            return
        self._buzzer.beep(on_time=on_time, off_time=off_time, n=n)


_buzzer_instance = None

def get_buzzer() -> StationBuzzer:
    global _buzzer_instance
    if _buzzer_instance is None:
        _buzzer_instance = StationBuzzer()
    return _buzzer_instance