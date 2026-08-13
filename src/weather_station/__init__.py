"""
SkyCast Weather Station - Professional Environmental Monitoring System
Version: 3.0.0
Tagline: "Your Environment, Understood"
"""

__version__ = "3.0.0"
__author__ = "SkyCast Team"
__project_name__ = "SkyCast Weather Station"
__tagline__ = "Your Environment, Understood"
__primary_color__ = "#0288d1"  # Primary blue for branding
__lcd_green__ = "#4caf50"  # Simulated LCD green

# Custom character definitions for LCD (smile, frown, sun, cloud, rain, moon, alert)
CUSTOM_CHARACTERS = {
    'smile': [0b00000, 0b00000, 0b01010, 0b00000, 0b10001, 0b01110, 0b00000, 0b00000],
    'frown': [0b00000, 0b00000, 0b01010, 0b00000, 0b01110, 0b10001, 0b00000, 0b00000],
    'sun': [0b00100, 0b01010, 0b00100, 0b11111, 0b00100, 0b01010, 0b00100, 0b00000],
    'cloud': [0b00000, 0b00110, 0b01111, 0b11111, 0b01111, 0b00110, 0b00000, 0b00000],
    'rain': [0b00100, 0b00100, 0b00100, 0b01110, 0b10101, 0b00100, 0b00000, 0b00000],
    'moon_new': [0b00000, 0b00110, 0b01111, 0b11111, 0b01111, 0b00110, 0b00000, 0b00000],
    'alert': [0b00100, 0b01110, 0b01110, 0b00100, 0b00100, 0b00000, 0b00100, 0b00000],
}

# Air quality status codes (non-truncating)
AQI_STATUS = {
    0: "OK",      # Good
    1: "Mod",     # Moderate
    2: "Sens",    # Sensitive groups
    3: "Unhl",    # Unhealthy
    4: "VUnh",    # Very Unhealthy
    5: "Hazd",    # Hazardous
}

# Comfort levels
COMFORT_LEVELS = {
    'comfortable': ("Comfort!", "smile"),
    'dry': ("Dry :(", "frown"),
    'humid': ("Humid :|", "frown"),
    'cold': ("Cold :(", "frown"),
    'hot': ("Hot :|", "frown"),
}
