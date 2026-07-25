"""LCD 16x2 Text Rendering Widgets with Cleaned UI."""
from datetime import datetime
from core.state import AppStateModel
from utils.formatting import format_temp


def render_widget_clock(snap: AppStateModel) -> tuple[str, str]:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    return f"Date: {date_str}", f"Time: {time_str}"


def render_widget_indoor(snap: AppStateModel) -> tuple[str, str]:
    t_str = format_temp(snap.indoor_temp, snap.temp_unit)
    h_str = f"{snap.indoor_humid:.0f}%" if snap.indoor_humid is not None else "N/A"
    
    comfort = "OK"
    if snap.indoor_temp is not None:
        if snap.indoor_temp > 28:
            comfort = "HOT"
        elif snap.indoor_temp < 18:
            comfort = "COLD"
        else:
            comfort = "GOOD"
            
    return f"In:{t_str} H:{h_str}", f"State:{comfort}"


def render_widget_outdoor(snap: AppStateModel) -> tuple[str, str]:
    t_str = format_temp(snap.outdoor_temp, snap.temp_unit)
    h_str = f"{snap.outdoor_humid}%" if snap.outdoor_humid is not None else "N/A"
    uv_str = str(snap.uv_current) if snap.uv_current is not None else "N/A"
    return f"Out:{t_str}", f"Humid:{h_str} UV:{uv_str}"


def render_widget_aqi(snap: AppStateModel) -> tuple[str, str]:
    raw_status = (snap.aqi_status or "").lower()
    
    # Standardized status indicator
    if "unhealthy" in raw_status or "hazardous" in raw_status or raw_status == "bad":
        status_text = "BAD"
    elif "moderate" in raw_status:
        status_text = "MOD"
    elif "good" in raw_status:
        status_text = "GOOD"
    else:
        status_text = snap.aqi_status[:4].upper() if snap.aqi_status else "N/A"

    return f"AQI:{snap.aqi_val} ({status_text})", f"P2.5:{snap.pm2_5_val} P10:{snap.pm10_val}"


def render_widget_pi(snap: AppStateModel) -> tuple[str, str]:
    return f"CPU:{snap.pi_cpu_temp} {snap.pi_cpu_usage}", f"RAM:{snap.pi_ram_usage}"


def render_widget_settings(snap: AppStateModel) -> tuple[str, str]:
    return "== SETTINGS ==", f"Unit:[{snap.temp_unit}] Bzg:[{snap.buzzer_mode}]"


WIDGET_MAP = {
    1: render_widget_clock,
    2: render_widget_indoor,
    3: render_widget_outdoor,
    4: render_widget_aqi,
    5: render_widget_pi,
}