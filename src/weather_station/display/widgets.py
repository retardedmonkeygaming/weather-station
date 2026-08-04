from datetime import datetime
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.utils.formatting import get_comfort_level, calculate_moon_phase
from weather_station.services.system import SystemService

def get_widget_text(widget_type: str) -> tuple:
    now = datetime.now()
    
    if widget_type == "widget_clock":
        return f"{now.strftime('%H:%M:%S'):^16}", f"{now.strftime('%d-%m-%y'):^16}"

    elif widget_type == "widget_indoor":
        if state.dht_error: return " [!] ERROR [!] ".center(16), " DHT11 MISSING ".center(16)
        comfort = get_comfort_level(state.indoor_temp, state.indoor_humid)
        t_str = f"{state.indoor_temp:.1f}C" if state.indoor_temp else "N/A"
        return f"In:{t_str}{state.temp_trend_symbol} H:{state.indoor_humid}%", f"State: {comfort} \x03"

    elif widget_type == "widget_outdoor":
        if state.wifi_error: return " [!] ERROR [!] ".center(16), " WIFI OFFLINE  ".center(16)
        return f"Out:{state.outdoor_temp}C {state.outdoor_humid}%", f"Fcst: {state.weather_icon} {state.weather_text}"

    elif widget_type == "widget_forecast":
        # UV Index Integration
        line1 = f"L:{state.outdoor_min} H:{state.outdoor_max}".center(16)
        line2 = f"UV:{state.uv_index} Peak:{state.uv_max}".center(16)
        return line1, line2

    elif widget_type == "widget_aqi":
        return f"AQI:{state.aqi_val} ({state.aqi_status})", f"P2.5:{state.pm2_5} P10:{state.pm10}"

    elif widget_type == "widget_moon":
        m = calculate_moon_phase()
        return f"Moon: \x07 {m['short_name']}", f"Illum: {m['illumination']}%"

    elif widget_type == "widget_pi":
        s = SystemService.get_stats()
        return f"CPU:{s['cpu_temp']} {s['cpu_usage']}", f"RAM:{s['ram_usage']}"

    return "Weather Station", "v3.0 Ready"

def get_settings_text() -> tuple:
    idx = state.settings_index
    if idx == 1: return "1. Temp Unit", f"> Mode: [{settings.unit}]"
    if idx == 2: return "2. Buzzer Mode", f"> Sound: [{settings.buzzer_mode}]"
    if idx == 3: return "3. Screen Power", "> Power: [ON]"
    if idx == 4: return "4. Auto Scroll", "> Rate: [OFF]"
    if idx == 5: return "5. Daily Alarm", "> State: [OFF]"
    if idx == 6: return "6. Alarm Hour", "> Hour: [17]"
    if idx == 7: return "7. Alarm Minute", "> Mins: [00]"
    if idx == 8: return "8. API Interval", f"> Rate: [{settings.api_rate}m]"
    if idx == 9: return "9. Log Interval", f"> Rate: [{settings.log_rate}m]"
    if idx == 10: return "10. Factory Reset", "> HOLD 3S RESET"
    
    # Message at the very end
    return " Settings Menu ".center(16), "View All WebUI ".center(16)