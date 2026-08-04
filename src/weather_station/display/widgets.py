from datetime import datetime
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.utils.formatting import get_comfort_level, calculate_moon_phase

def get_widget_text(widget_type: str) -> tuple:
    now = datetime.now()
    
    if widget_type == "widget_clock":
        # Page 1: Clock & Date (Restored Prefixes)
        line1 = f"{state.clock_icon} Time: {now.strftime('%H:%M:%S')}"
        line2 = f"  Date: {now.strftime('%d-%m-%Y')}"
        return line1, line2

    elif widget_type == "widget_indoor":
        # Page 2: Indoor
        if state.dht_error: return "In: ERR [DHT11]", "State: Check"
        comfort = get_comfort_level(state.indoor_temp, state.indoor_humid)
        t_str = f"{state.indoor_temp:.1f}C" if state.indoor_temp else "N/A"
        return f"In:{t_str}{state.temp_trend_symbol} H:{state.indoor_humid}%", f"State: {comfort} \x03"

    elif widget_type == "widget_outdoor":
        # Page 3: Outdoor
        status = " [OFF]" if state.wifi_error else ""
        return f"Out:{state.outdoor_temp}C {state.outdoor_humid}%{status}", "Fcst: Clear \x05"

    elif widget_type == "widget_forecast":
        # Page 4: Min/Max
        return f"L:{state.outdoor_min} H:{state.outdoor_max}", "Daily Forecast"

    elif widget_type == "widget_aqi":
        # Page 5: Air Quality
        return f"AQI:{state.aqi_val} ({state.aqi_status})", "Air Quality Index"

    elif widget_type == "widget_moon":
        # Page 6: Moon
        m = calculate_moon_phase()
        return f"Moon: \x07 {m['short_name']}", f"Illum: {m['illumination']}%"

    return "Weather Station", "v3.0 Ready"

def get_settings_text() -> tuple:
    """Restores the 10 Settings Menu Pages."""
    idx = state.settings_index
    if idx == 1: return "1. Temp Unit", f"> Mode: [{settings.unit}]"
    if idx == 2: return "2. Buzzer Mode", f"> Sound: [{settings.buzzer_mode}]"
    if idx == 3: return "3. Screen Power", "> Power: [ON]"
    if idx == 4: return "4. Auto Scroll", f"> Rate: [{settings.api_rate}m]"
    if idx == 5: return "5. Daily Alarm", "> State: [OFF]"
    if idx == 6: return "6. Alarm Hour", "> Hour: [17]"
    if idx == 7: return "7. Alarm Minute", "> Mins: [00]"
    if idx == 8: return "8. API Interval", f"> Rate: [{settings.api_rate}m]"
    if idx == 9: return "9. Log Interval", f"> Rate: [{settings.log_rate}m]"
    if idx == 10: return "10. Factory Reset", "> HOLD 3S RESET"
    return "Settings", "Unknown Option"