"""HD44780 16x2 Character LCD Driver Wrapper."""
import board
import digitalio
import adafruit_character_lcd.character_lcd as character_lcd
from hardware.pins import (
    LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7, LCD_COLUMNS, LCD_ROWS
)

class LCDDriver:
    def __init__(self):
        rs = digitalio.DigitalInOut(getattr(board, f"D{LCD_RS}"))
        en = digitalio.DigitalInOut(getattr(board, f"D{LCD_EN}"))
        d4 = digitalio.DigitalInOut(getattr(board, f"D{LCD_D4}"))
        d5 = digitalio.DigitalInOut(getattr(board, f"D{LCD_D5}"))
        d6 = digitalio.DigitalInOut(getattr(board, f"D{LCD_D6}"))
        d7 = digitalio.DigitalInOut(getattr(board, f"D{LCD_D7}"))

        self.lcd = character_lcd.Character_LCD_Mono(
            rs, en, d4, d5, d6, d7, LCD_COLUMNS, LCD_ROWS
        )

    def write_lines(self, line1: str, line2: str):
        l1 = line1[:16].ljust(16)
        l2 = line2[:16].ljust(16)
        self.lcd.message = f"{l1}\n{l2}"

    def set_backlight(self, enabled: bool):
        self.lcd.backlight = enabled

    def create_char(self, location: int, pattern: list):
        self.lcd.create_char(location, pattern)

    def clear(self):
        self.lcd.clear()