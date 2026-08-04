from datetime import datetime
from weather_station.core.state import state
from weather_station.utils.formatting import get_comfort_level, calculate_moon_phase

def get_widget_text(widget_type: str) -> tuple:
    now = datetime.now()
    
    if widget_type == "widget_clock":
        # Page 1: Centered Time & Date (Year shortened to 2-digit)
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%d-%m-%y")
        # Centering on 16 chars: (16 - len) // 2 spaces
        line1 = f"{time_str:^16}"
        line2 = f"{date_str:^16}"
        return line1, line2

    elif widget_type == "widget_indoor":
        if state.dht_error: return "In: ERR [DHT11]", "State: Check"
        comfort = get_comfort_level(state.indoor_temp, state.indoor_humid)
        t_str = f"{state.indoor_temp:.1f}C" if state.indoor_temp else "N/A"
        # Match your old style: "In:25.4C-> H:40%"
        return f"In:{t_str}{state.temp_trend_symbol} H:{state.indoor_humid}%", f"State: {comfort} \x03"

    elif widget_type == "widget_outdoor":
        status = "!" if state.wifi_error else ""
        return f"Out:{state.outdoor_temp}C {state.outdoor_humid}%{status}", f"Fcst: {state.weather_icon} {state.weather_text}"

    elif widget_type == "widget_forecast":
        # Centered Min/Max
        line1 = f"L:{state.outdoor_min} H:{state.outdoor_max}"
        return f"{line1:^16}", f"{'Daily Forecast':^16}"

    elif widget_type == "widget_aqi":
        # Restore old AQI Layout
        return f"AQI:{state.aqi_val} ({state.aqi_status})", f"P2.5:{state.pm2_5} P10:{state.pm10}"

    elif widget_type == "widget_moon":
        m = calculate_moon_phase()
        # Restore: "Moon: [Icon] [Name]"
        return f"Moon: \x07 {m['short_name']}", f"Illum: {m['illumination']}%"

    return "Weather Station", "v3.0"