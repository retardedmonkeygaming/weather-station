import math
from datetime import datetime

def calculate_moon_phase(dt=None):
    if dt is None: dt = datetime.now()
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
    if temp_c is None or humid is None:
        return "Unknown"
    try:
        t, h = float(temp_c), float(humid)
        if t > 29: return "Hot"
        if h < 30: return "Dry"
        if h > 65: return "Humid"
        if 20 <= t <= 26 and 30 <= h <= 60: return "Comfort"
        return "Moderate"
    except:
        return "Unknown"