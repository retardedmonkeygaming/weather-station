import math
from datetime import datetime

def calculate_moon_phase(dt=None):
    """Calculates moon phase, illumination, and name."""
    if dt is None:
        dt = datetime.now()
    ref_date = datetime(2000, 1, 6, 18, 14)
    diff = dt - ref_date
    days = diff.total_seconds() / 86400.0
    moon_age = days % 29.530588853
    
    if moon_age < 1.84: phase = "New Moon"
    elif moon_age < 5.53: phase = "Waxing Crescent"
    elif moon_age < 9.22: phase = "First Quarter"
    elif moon_age < 12.91: phase = "Waxing Gibbous"
    elif moon_age < 16.61: phase = "Full Moon"
    elif moon_age < 20.30: phase = "Waning Gibbous"
    elif moon_age < 23.99: phase = "Last Quarter"
    elif moon_age < 27.68: phase = "Waning Crescent"
    else: phase = "New Moon"
    
    illum = round((1 - math.cos((moon_age / 29.53) * 2 * math.pi)) / 2 * 100)
    return {"short_name": phase, "illumination": illum}

def get_comfort_level(temp_c, humid):
    """Determines comfort level based on temp and humidity."""
    if temp_c is None or humid is None:
        return "Unknown"
    try:
        temp_c = float(temp_c)
        humid = float(humid)
    except (ValueError, TypeError):
        return "Unknown"

    if temp_c > 29: return "Hot"
    if humid < 30: return "Dry"
    if humid > 65: return "Humid"
    if 20 <= temp_c <= 26 and 30 <= humid <= 60: return "Comfort"
    return "Moderate"

def format_centered_clock():
    """Returns centered Time and Date (YY) for the 16x2 LCD."""
    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%d-%m-%y") # Shortened year (e.g. 26)
    
    return f"{time_str:^16}", f"{date_str:^16}"