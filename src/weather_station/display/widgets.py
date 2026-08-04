from datetime import datetime
from weather_station.core.state import state
from weather_station.utils.formatting import get_comfort_level, calculate_moon_phase
from weather_station.services.system import SystemService

def get_widget_text(widget_type: str) -> tuple:
    now = datetime.now()
    
    if widget_type == "widget_clock":
        # Page 1: Clock & Date
        return now.strftime("Time: %H:%M:%S"), now.strftime("Date: %d-%m-%Y")

    elif widget_type == "widget_indoor":
        # Page 2: Indoor Stats
        if state.dht_error: return "In: ERR [DHT11]", "Check Sensor"
        comfort = get_comfort_level(state.indoor_temp, state.indoor_humid)
        return f"In:{state.indoor_temp}C H:{state.indoor_humid}%", f"State: {comfort} \x03"

    elif widget_type == "widget_outdoor":
        # Page 3: Outdoor Stats
        status = "!" if state.wifi_error else ""
        return f"Out:{state.outdoor_temp}C {state.outdoor_humid}%{status}", "Fcst: Clear \x05"

    elif widget_type == "widget_aqi":
        # Page 4: Air Quality
        return f"AQI:{state.aqi_val or 'N/A'}", "P2.5:N/A P10:N/A"

    elif widget_type == "widget_pi":
        # Page 5: System Health
        stats = SystemService.get_stats()
        return f"CPU:{stats['cpu_temp']} {stats['cpu_usage']}", f"RAM:{stats['ram_usage']}"

    elif widget_type == "widget_moon":
        # Page 6: Moon Phase
        moon = calculate_moon_phase()
        return f"Moon: {moon['short_name']}", f"Illum: {moon['illumination']}%"

    return "Weather Station", "v3.0 Modular"