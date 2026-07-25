"""LCD 16x2 Text Rendering Widgets with Title-Case Formatting."""
from datetime import datetime
from core.state import AppStateModel
from utils.formatting import format_temp


def render_widget_clock(snap: AppStateModel) -> tuple[str, str]:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    return f"Date: {date_str}", f"Time: {time_str}"


def render_widget_indoor(snap: AppStateModel) -> tuple[str, str]:
    calibrated_temp = snap.indoor_temp + snap.temp_offset if snap.indoor_temp is not None else None
    t_str = format_temp(calibrated_temp, snap.temp_unit)
    h_str = f"{snap.indoor_humid:.0f}%" if snap.indoor_humid is not None else "N/A"
    
    if calibrated_temp is None:
        comfort = "Offline"
    elif calibrated_temp > 28:
        comfort = "Hot"
    elif calibrated_temp < 18:
        comfort = "Cold"
    else:
        comfort = "Comfort"
            
    return f"In: {t_str}  H:{h_str}", f"State: {comfort}"


def render_widget_outdoor(snap: AppStateModel) -> tuple[str, str]:
    t_str = format_temp(snap.outdoor_temp, snap.temp_unit)
    h_str = f"{snap.outdoor_humid}%" if snap.outdoor_humid is not None else "N/A"
    uv_str = str(snap.uv_current) if snap.uv_current is not None else "N/A"
    return f"Out: {t_str}", f"Hum: {h_str} UV: {uv_str}"


def render_widget_aqi(snap: AppStateModel) -> tuple[str, str]:
    raw_status = (snap.aqi_status or "").lower()
    
    if "unhealthy" in raw_status or "hazardous" in raw_status or raw_status == "bad":
        status_text = "Bad"
    elif "moderate" in raw_status:
        status_text = "Moderate"
    elif "good" in raw_status:
        status_text = "Good"
    else:
        status_text = snap.aqi_status.capitalize() if snap.aqi_status else "N/A"

    return f"AQI: {snap.aqi_val} ({status_text})", f"P2.5:{snap.pm2_5_val} P10:{snap.pm10_val}"


def render_widget_pi(snap: AppStateModel) -> tuple[str, str]:
    return f"CPU: {snap.pi_cpu_temp} {snap.pi_cpu_usage}", f"RAM: {snap.pi_ram_usage}"


def render_widget_settings(snap: AppStateModel) -> tuple[str, str]:
    """Scrollable row-based settings interface for 7 settings."""
    idx = snap.settings_page_index
    total = snap.total_settings_count
    header = f"Settings [{idx + 1}/{total}]"

    if idx == 0:
        line2 = f"> Unit: [{snap.temp_unit}]"
    elif idx == 1:
        line2 = f"> Buzzer: [{snap.buzzer_mode}]"
    elif idx == 2:
        log_m = int(snap.log_interval / 60)
        line2 = f"> Log Rate: [{log_m}m]"
    elif idx == 3:
        api_m = int(snap.api_fetch_interval / 60)
        line2 = f"> API Rate: [{api_m}m]"
    elif idx == 4:
        sign = "+" if snap.temp_offset > 0 else ""
        line2 = f"> Offset: [{sign}{snap.temp_offset:.1f}C]"
    elif idx == 5:
        mode_str = "ON" if snap.night_mode else "OFF"
        line2 = f"> NightMode: [{mode_str}]"
    elif idx == 6:
        line2 = "> Reset Settings"
    else:
        line2 = "> Exit"

    return header, line2


WIDGET_MAP = {
    1: render_widget_clock,
    2: render_widget_indoor,
    3: render_widget_outdoor,
    4: render_widget_aqi,
    5: render_widget_pi,
}