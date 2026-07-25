"""Formatting utilities for temperature and weather values."""

def format_temp(temp_c: float | None, unit: str = "C") -> str:
    """Format temperature value to Celsius or Fahrenheit string."""
    if temp_c is None:
        return "N/A"
    
    if unit.upper() == "F":
        temp_val = (temp_c * 9 / 5) + 32
        return f"{temp_val:.1f}°F"
    
    return f"{temp_c:.1f}°C"