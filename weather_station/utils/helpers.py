"""
Utility Functions
Common helpers used across the application.
"""

import math
from datetime import datetime
from typing import Optional, Tuple


def calculate_moon_phase(dt: Optional[datetime] = None) -> Tuple[str, str, int, float]:
    """
    Calculate moon phase for a given date.
    
    Returns:
        Tuple of (phase_name, short_name, illumination_percent, age_days)
    """
    if dt is None:
        dt = datetime.now()
    
    ref_date = datetime(2000, 1, 6, 18, 14)
    diff = dt - ref_date
    days = diff.total_seconds() / 86400.0
    moon_age = days % 29.5305877057
    
    illumination = round((1 - math.cos((moon_age / 29.5305877057) * 2 * math.pi)) / 2 * 100)
    
    if moon_age < 1.84566:
        phase_name = "New Moon"
        short_name = "New Moon"
    elif moon_age < 5.53699:
        phase_name = "Waxing Crescent"
        short_name = "Wax Crescent"
    elif moon_age < 9.22831:
        phase_name = "First Quarter"
        short_name = "1st Quarter"
    elif moon_age < 12.91963:
        phase_name = "Waxing Gibbous"
        short_name = "Wax Gibbous"
    elif moon_age < 16.61096:
        phase_name = "Full Moon"
        short_name = "Full Moon"
    elif moon_age < 20.30228:
        phase_name = "Waning Gibbous"
        short_name = "Wan Gibbous"
    elif moon_age < 23.99361:
        phase_name = "Last Quarter"
        short_name = "3rd Quarter"
    elif moon_age < 27.68493:
        phase_name = "Waning Crescent"
        short_name = "Wan Crescent"
    else:
        phase_name = "New Moon"
        short_name = "New Moon"
    
    return phase_name, short_name, illumination, round(moon_age, 1)


def format_temperature(celsius: Optional[float], unit: str = "C") -> str:
    """
    Format temperature value with unit.
    
    Args:
        celsius: Temperature in Celsius
        unit: 'C' for Celsius, 'F' for Fahrenheit
    
    Returns:
        Formatted string like "24.5C" or "76.1F"
    """
    if celsius is None:
        return "N/A"
    
    try:
        val = float(celsius)
        if unit == "F":
            converted = (val * 9/5) + 32
            return f"{converted:.1f}F"
        return f"{val:.1f}C"
    except (ValueError, TypeError):
        return "N/A"


def get_comfort_level(temp_c: Optional[float], humidity: Optional[float]) -> str:
    """
    Determine comfort level based on temperature and humidity.
    
    Returns:
        Comfort description string
    """
    if temp_c is None or humidity is None:
        return "Unknown"
    
    if temp_c > 29:
        return "Hot"
    if humidity < 30:
        return "Dry"
    if humidity > 65:
        return "Humid"
    if 20 <= temp_c <= 26 and 30 <= humidity <= 60:
        return "Comfort"
    return "Moderate"


def get_weather_info(code: int) -> Tuple[str, str]:
    """
    Get weather icon and description from WMO code.
    
    Returns:
        Tuple of (icon_char, description)
    """
    if code in [0, 1]:
        return ("Clear", "Clear")
    if code in [2, 3]:
        return ("Cloudy", "Cloudy")
    if code in [45, 48]:
        return ("Foggy", "Foggy")
    if code in [51, 53, 55, 61, 63, 65]:
        return ("Rain", "Rain")
    if code in [71, 73, 75]:
        return ("Snow", "Snow")
    if code in [77, 85, 86]:
        return ("Snow", "Snow")
    if code in [80, 81, 82]:
        return ("Rain", "Rain showers")
    if code in [95, 96, 99]:
        return ("Storm", "Thunderstorm")
    return ("Clear", "Unknown")


def parse_aqi_status(aqi: Optional[int]) -> str:
    """
    Convert AQI value to status string.
    
    Returns:
        Short status string (OK, Mod, Sens, etc.)
    """
    if aqi is None:
        return "N/A"
    
    try:
        val = int(aqi)
        if val <= 50:
            return "Good"
        if val <= 100:
            return "Moderate"
        if val <= 150:
            return "Sensitiv"
        if val <= 200:
            return "Unhealth"
        if val <= 300:
            return "V.Unhlth"
        return "Hazard"
    except (ValueError, TypeError):
        return "N/A"


def get_pi_system_stats() -> dict:
    """
    Get Raspberry Pi system statistics.
    
    Returns:
        Dictionary with cpu_temp, cpu_usage, ram_usage
    """
    import os
    
    stats = {
        "cpu_temp": "N/A",
        "cpu_usage": "N/A",
        "ram_usage": "N/A"
    }
    
    # CPU Temperature
    try:
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read().strip()) / 1000.0
                stats["cpu_temp"] = f"{temp:.1f}C"
    except Exception:
        pass
    
    # CPU Usage
    try:
        with open("/proc/stat", "r") as f:
            fields = [float(column) for column in f.readline().strip().split()[1:]]
            idle, total = fields[3], sum(fields)
            usage = 100.0 * (1.0 - idle / total)
            stats["cpu_usage"] = f"{usage:.1f}%"
    except Exception:
        pass
    
    # RAM Usage
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
            mem_total = int(lines[0].split()[1])
            mem_available = int(lines[2].split()[1])
            usage = 100.0 * (1.0 - mem_available / mem_total)
            stats["ram_usage"] = f"{usage:.1f}%"
    except Exception:
        pass
    
    return stats


def is_quiet_hours(start_hour: int = 23, end_hour: int = 7) -> bool:
    """Check if current time is within quiet hours"""
    hour = datetime.now().hour
    return hour >= start_hour or hour < end_hour


def truncate_text(text: str, max_length: int = 16) -> str:
    """Truncate text to fit LCD line"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 2] + ".."


def pad_lines(line1: str, line2: str, width: int = 16) -> Tuple[str, str]:
    """Pad lines to fixed width for consistent display"""
    l1 = (line1 + " " * width)[:width]
    l2 = (line2 + " " * width)[:width]
    return l1, l2
