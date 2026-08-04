import math
from datetime import datetime

def calculate_moon_phase(dt=None):
    if dt is None: dt = datetime.now()
    # Your original moon logic remains here, but returning a clean dictionary
    # ... (logic) ...
    return {
        "phase_name": "Full Moon", 
        "illumination": 100, 
        "short_name": "Full"
    }

def get_comfort_level(temp_c, humid):
    if temp_c is None or humid is None: return "Unknown"
    if temp_c > 29: return "Hot"
    if humid < 30: return "Dry"
    if humid > 65: return "Humid"
    if 20 <= temp_c <= 26 and 30 <= humid <= 60: return "Comfort"
    return "Moderate"