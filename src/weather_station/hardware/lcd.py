import board
import digitalio
import adafruit_character_lcd.character_lcd as character_lcd
from weather_station.hardware.pins import LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7

class WeatherLCD:
    def __init__(self):
        # Initializing Pins using DigitalInOut
        rs = digitalio.DigitalInOut(getattr(board, f"D{LCD_RS}"))
        en = digitalio.DigitalInOut(getattr(board, f"D{LCD_EN}"))
        d4 = digitalio.DigitalInOut(getattr(board, f"D{LCD_D4}"))
        d5 = digitalio.DigitalInOut(getattr(board, f"D{LCD_D5}"))
        d6 = digitalio.DigitalInOut(getattr(board, f"D{LCD_D6}"))
        d7 = digitalio.DigitalInOut(getattr(board, f"D{LCD_D7}"))

        self.lcd = character_lcd.Character_LCD_Mono(
    rs, en, d4, d5, d6, d7, columns=16, lines=2
)
        self._create_custom_chars()

    def _create_custom_chars(self):
        """Pre-load the bitmaps you defined in your original script."""
        self.lcd.create_char(0, [31, 17, 10, 4, 10, 21, 31, 0])   # Hourglass 1
        self.lcd.create_char(1, [31, 21, 4, 10, 17, 17, 31, 0])   # Hourglass 2
        self.lcd.create_char(2, [4, 14, 14, 14, 31, 31, 4, 0])    # Alarm Bell
        self.lcd.create_char(3, [0, 10, 0, 4, 17, 14, 0, 0])      # Smile Face
        self.lcd.create_char(4, [0, 14, 31, 31, 31, 14, 0, 0])    # Cloud
        self.lcd.create_char(5, [4, 21, 14, 31, 14, 21, 4, 0])    # Sun
        self.lcd.create_char(6, [31, 31, 31, 31, 31, 31, 31, 31]) # Loading Block
        # Char 7 is reserved for dynamic Moon phases

    def update_moon_icon(self, bitmap: list):
        self.lcd.create_char(7, bitmap)

    def write_lines(self, line1: str, line2: str):
        """Main method to update the screen. Pads strings to clear old chars."""
        self.lcd.message = f"{line1[:16]:<16}\n{line2[:16]:<16}"

    def clear(self):
        self.lcd.clear()