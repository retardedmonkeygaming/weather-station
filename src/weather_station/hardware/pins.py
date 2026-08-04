"""
Single source of truth for GPIO pin mapping.
Using BCM pin numbering.
"""

# LCD 1602A (HD44780 Parallel 4-bit mode)
LCD_RS = 22
LCD_EN = 17
LCD_D4 = 25
LCD_D5 = 24
LCD_D6 = 23
LCD_D7 = 18

# Sensors
DHT_PIN = 4        # DHT11 Data
TOUCH_PIN = 27     # Touch Sensor Button

# Actuators
BUZZER_PIN = 2     # Active Buzzer