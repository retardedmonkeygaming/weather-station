"""HD44780 LCD Hardware Driver with Custom Matrix Emojis."""
import board
import digitalio
import adafruit_character_lcd.character_lcd as character_lcd
from hardware.pins import (
    LCD_RS, LCD_E, LCD_D4, LCD_D5, LCD_D6, LCD_D7,
    LCD_COLUMNS, LCD_ROWS
)

# Custom 5x8 Pixel Matrices
CUSTOM_CHARACTERS = {
    "happy": [0x00, 0x0A, 0x00, 0x04, 0x11, 0x0E, 0x00, 0x00],
    "sad":   [0x00, 0x0A, 0x00, 0x04, 0x00, 0x0E, 0x11, 0x00],
    "degree":[0x0C, 0x12, 0x12, 0x0C, 0x00, 0x00, 0x00, 0x00],
    "bell":  [0x04, 0x0E, 0x0E, 0x0E, 0x1F, 0x00, 0x04, 0x00],
    "wifi":  [0x00, 0x0E, 0x11, 0x04, 0x0A, 0x00, 0x04, 0x00],
}


class LCDDriver:
    def __init__(self):
        try:
            rs = digitalio.DigitalInOut(LCD_RS)
            en = digitalio.DigitalInOut(LCD_E)
            d4 = digitalio.DigitalInOut(LCD_D4)
            d5 = digitalio.DigitalInOut(LCD_D5)
            d6 = digitalio.DigitalInOut(LCD_D6)
            d7 = digitalio.DigitalInOut(LCD_D7)

            self.lcd = character_lcd.Character_LCD_Mono(
                rs, en, d4, d5, d6, d7, LCD_COLUMNS, LCD_ROWS
            )
            self.lcd.clear()
            self._load_custom_characters()
            self.available = True
        except Exception as e:
            print(f"[LCD HARDWARE WARNING]: Operating in headless/mock mode ({e})")
            self.available = False

    def _load_custom_characters(self):
        if not self.available:
            return
        # Load custom bitmap definitions into LCD CGRAM slots (0-4)
        for idx, (name, pattern) in enumerate(CUSTOM_CHARACTERS.items()):
            try:
                self.lcd.create_char(idx, pattern)
            except Exception:
                pass

    def clear(self):
        if self.available:
            self.lcd.clear()

    def write_lines(self, line1: str, line2: str):
        line1_pad = line1.ljust(16)[:16]
        line2_pad = line2.ljust(16)[:16]
        
        if self.available:
            self.lcd.home()
            self.lcd.message = f"{line1_pad}\n{line2_pad}"
        else:
            # Console LCD Preview Output
            print(f"┌────────────────┐\n│{line1_pad}│\n│{line2_pad}│\n└────────────────┘")