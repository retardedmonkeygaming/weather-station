from datetime import datetime
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.utils.formatting import get_comfort_level, calculate_moon_phase
from weather_station.services.system import SystemService

def get_widget_text(widget_type: str) -> tuple:
    now = datetime.now()
    if widget_type == "widget_indoor":
        if state.dht_error: return "In: ERR [DHT11]", "Check Sensor"
        comfort = get_comfort_level(state.indoor_temp, state.indoor_humid)
        return f"In:{state.indoor_temp:.1f}C{state.temp_trend_symbol} H:{state.indoor_humid}%", f"State: {comfort} \x03"

    elif widget_type == "widget_outdoor":
        return f"Out:{state.outdoor_temp}C {state.outdoor_humid}%", f"Fcst: {state.weather_icon} {state.weather_text}"

    elif widget_type == "widget_clock":
        return f"Time: {now.strftime('%H:%M:%S')}", f"Date: {now.strftime('%d-%m-%y')}"

    elif widget_type == "widget_pi":
        s = SystemService.get_stats()
        return f"CPU:{s['cpu_temp']} {s['cpu_usage']}", f"RAM:{s['ram_usage']}"

    elif widget_type == "widget_moon":
        m = calculate_moon_phase()
        return f"Moon: \x07 {m['short_name']}", f"Illum: {m['illumination']}%"

    elif widget_type == "widget_aqi":
        return f"AQI:{state.aqi_val} ({state.aqi_status})", f"P2.5:{state.pm2_5} P10:{state.pm10}"

    elif widget_type == "widget_forecast":
        return f"L:{state.outdoor_min} H:{state.outdoor_max}", f"UV:{state.uv_index} Peak:{state.uv_max}"
    
    return "Weather Station", "v3.0 Ready"

def get_settings_text() -> tuple:
    # Restored literally from your settings logic
    idx = state.settings_index
    if idx == 1: return "1. Temp Unit", f"> Mode: [{settings.unit}]"
    if idx == 2: return "2. Buzzer Mode", f"> Sound: [{settings.buzzer_mode}]"
    if idx == 3: return "3. Screen Power", "> Power: [ON]"
    if idx == 10: return "10. Factory Reset", "> HOLD 3S RESET"
    return f"Setting {idx}", "View on WebUI"