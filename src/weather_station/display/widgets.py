from datetime import datetime
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.utils.formatting import get_comfort_level, calculate_moon_phase
from weather_station.services.system import SystemService

def get_widget_text(widget_type: str) -> tuple:
    now = datetime.now()
    if widget_type == "widget_indoor":
        if state.dht_error: return "In: ERR [DHT11]", "State: Check"
        comfort = get_comfort_level(state.indoor_temp, state.indoor_humid)
        return f"In:{state.indoor_temp:.1f}C{state.temp_trend_symbol} H:{state.indoor_humid}%", f"State: {comfort} \x03"
    elif widget_type == "widget_outdoor":
        return f"Out:{state.outdoor_temp}C {state.outdoor_humid}%", f"Fcst: {state.weather_icon} {state.weather_text}"
    elif widget_type == "widget_aqi":
        return f"AQI:{state.aqi_val} ({state.aqi_status})", f"P2.5:{state.pm2_5} P10:{state.pm10}"
    elif widget_type == "widget_pi":
        s = SystemService.get_stats()
        return f"CPU:{s['cpu_temp']} {s['cpu_usage']}", f"RAM:{s['ram_usage']}"
    elif widget_type == "widget_clock":
        return f"Time: {now.strftime('%H:%M:%S')}", f"Date: {now.strftime('%d-%m-%y')}"
    elif widget_type == "widget_moon":
        m = calculate_moon_phase()
        return f"Moon: \x07 {m['short_name']}", f"Illum: {m['illumination']}%"
    elif widget_type == "widget_humidity":
        return f"Humidity: {state.indoor_humid}%", "Indoor Air Damp"
    elif widget_type == "widget_uv":
        return f"UV Index: {state.uv_index}", f"Peak: {state.uv_max}"
    elif widget_type == "widget_pm":
        return f"PM2.5: {state.pm2_5}", f"PM10: {state.pm10}"
    elif widget_type == "widget_forecast":
        return f"L:{state.outdoor_min} H:{state.outdoor_max}", f"UV:{state.uv_index} P:{state.uv_max}"
    elif widget_type == "widget_comfort":
        comfort = get_comfort_level(state.indoor_temp, state.indoor_humid)
        return f"In:{state.indoor_temp:.1f}C H:{state.indoor_humid}%", f"Comfort: {comfort}"
    elif widget_type == "widget_status":
        d_st = "OK" if not state.dht_error else "ERR"
        w_st = "OK" if not state.wifi_error else "ERR"
        return f"DHT:{d_st} WiFi:{w_st}", "Station Active"
    return "Weather Station", "v3.0 Ready"

def get_settings_text() -> tuple:
    """Display settings menu with all 10 options properly formatted for 16x2 LCD."""
    idx = state.settings_index
    
    # Settings menu - each option fits on 16x2 LCD
    settings_menu = {
        1: ("1. Temp Unit", f"> [{settings.unit}] C/F"),
        2: ("2. Buzzer Mode", f"> [{settings.buzzer_mode}]"),
        3: ("3. Screen Power", "> [ON] Always"),
        4: ("4. Auto Scroll", "> [OFF] Disabled"),
        5: ("5. Daily Alarm", "> [OFF] Disabled"),
        6: ("6. Alert Temp Hi", "> [35C] Threshold"),
        7: ("7. Alert Temp Lo", "> [10C] Threshold"),
        8: ("8. Sensor Offset", "> [0.0C] Calib"),
        9: ("9. Quiet Hours", "> [22-07] Hrs"),
        10: ("10. Factory Reset", "> HOLD 3S RESET")
    }
    
    return settings_menu.get(idx, (f"Setting {idx}", "View on WebUI"))