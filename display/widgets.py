"""LCD 16x2 Text Rendering Widgets."""
from core.state import AppStateModel
from utils.formatting import format_temp

def render_widget_indoor(snap: AppStateModel) -> tuple[str, str]:
    t_str = format_temp(snap.indoor_temp, snap.temp_unit)
    h_str = f"{snap.indoor_humid:.0f}%" if snap.indoor_humid is not None else "N/A"
    return f"In:{t_str}", f"Humid:{h_str}"

def render_widget_outdoor(snap: AppStateModel) -> tuple[str, str]:
    t_str = format_temp(snap.outdoor_temp, snap.temp_unit)
    h_str = f"{snap.outdoor_humid}%" if snap.outdoor_humid is not None else "N/A"
    return f"Out:{t_str}", f"Humid:{h_str}"

def render_widget_aqi(snap: AppStateModel) -> tuple[str, str]:
    return f"AQI:{snap.aqi_val} ({snap.aqi_status})", f"P2.5:{snap.pm2_5_val} P10:{snap.pm10_val}"

def render_widget_pi(snap: AppStateModel) -> tuple[str, str]:
    return f"CPU:{snap.pi_cpu_temp} {snap.pi_cpu_usage}", f"RAM:{snap.pi_ram_usage}"

def render_widget_status(snap: AppStateModel) -> tuple[str, str]:
    dht_str = "ERR" if snap.dht_error else "OK"
    wifi_str = "ERR" if snap.wifi_error else "OK"
    return f"DHT:{dht_str}  WiFi:{wifi_str}", "Station Active"

WIDGET_MAP = {
    "widget_indoor": render_widget_indoor,
    "widget_outdoor": render_widget_outdoor,
    "widget_aqi": render_widget_aqi,
    "widget_pi": render_widget_pi,
    "widget_status": render_widget_status,
}