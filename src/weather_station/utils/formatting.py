import math
from datetime import datetime

def calculate_moon_phase(dt=None):
    # ... (keep math logic) ...
    # Updated phase naming to initials
    phase_map = {
        "New Moon": "New",
        "Waxing Crescent": "W.X.C",
        "First Quarter": "1st.Q",
        "Waxing Gibbous": "W.X.G",
        "Full Moon": "Full",
        "Waning Gibbous": "W.N.G",
        "Last Quarter": "3rd.Q",
        "Waning Crescent": "W.N.C"
    }
    short_name = phase_map.get(phase, "N/A")
    return {"short_name": short_name, "illumination": illum}

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