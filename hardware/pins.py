"""GPIO Pin Assignments for Raspberry Pi Hardware Interfacing."""
import board

# LCD 16x2 Pin Assignments (HD44780 Parallel Wiring)
LCD_RS = board.D22      # Register Select
LCD_E = board.D17       # Enable Pin (LCD_E)
LCD_D4 = board.D25      # Data Pin 4
LCD_D5 = board.D24      # Data Pin 5
LCD_D6 = board.D23      # Data Pin 6
LCD_D7 = board.D18      # Data Pin 7

LCD_COLUMNS = 16
LCD_ROWS = 2

# Touch Sensor Input Pin
TOUCH_PIN = 27          # BCM GPIO Pin 27 for Touch Input

# Buzzer Pin
BUZZER_PIN = 12         # BCM GPIO Pin 12 for Buzzer