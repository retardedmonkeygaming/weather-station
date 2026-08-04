from datetime import datetime
from weather_station.core.state import state
from weather_station.utils.formatting import get_comfort_level

def get_widget_text(widget_type: str) -> tuple:
    """Returns (Line1, Line2) for a given widget type."""
    if widget_type == "widget_indoor":
        if state.dht_error: return "In: ERR [DHT11]", "Check Sensor"
        comfort = get_comfort_level(state.indoor_temp, state.indoor_humid)
        return f"In:{state.indoor_temp}C H:{state.indoor_humid}%", f"State: {comfort} \x03"

    elif widget_type == "widget_clock":
        now = datetime.now()
        return now.strftime("%H:%M:%S"), now.strftime("%d-%m-%Y")

    elif widget_type == "widget_outdoor":
        return f"Out:{state.outdoor_temp}C {state.outdoor_humid}%", "Fcst: Clear \x05"

    # Default fallback
    return "Weather Station", "v3.0 Loading..."