"""LCD 16x2 Text Rendering Widgets with Title-Case Formatting & Extra Pages."""
import time
from datetime import datetime
from core.state import AppStateModel
from utils.formatting import format_temp

# System boot timestamp for uptime calculation
START_TIME = time.time()


def get_moon_phase(date_obj: datetime) -> str:
    """Calculate current moon phase using Conway's algorithm approximation."""
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day

    if month < 3:
        year -= 1
        month += 12

    month += 1
    c = 365.25 * year
    e = 30.6 * month
    jd = c + e + day - 694039.09  # Julian date relative to epoch
    jd /= 29.5305882  # Divide by synodic month length
    b = int(jd)
    jd -= b  # Fractional part gives position in lunar cycle (0.0 - 1.0)
    phase_val = round(jd * 8) % 8

    phases = [
        "New Moon",
        "Waxing Cres",
        "First Qtr",
        "Waxing Gibb",
        "Full Moon",
        "Waning Gibb",
        "Third Qtr",
        "Waning Cres",
    ]
    return phases[phase_val]


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

    return f"In: {t_str} H:{h_str}", f"State: {comfort}"


def render_widget_outdoor(snap: AppStateModel) -> tuple[str, str]:
    """Updated Outdoor Widget: Line 1 has temp & humidity; Line 2 has UV & Max UV."""
    t_str = format_temp(snap.outdoor_temp, snap.temp_unit)
    h_str = f"{snap.outdoor_humid:.0f}%" if snap.outdoor_humid is not None else "N/A"
    uv_str = f"{snap.uv_current:.1f}" if snap.uv_current is not None else "N/A"
    uv_max_str = f"{snap.uv_max:.1f}" if snap.uv_max is not None else "N/A"

    return f"Out: {t_str} H:{h_str}", f"UV: {uv_str} Max: {uv_max_str}"


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


def render_widget_moon(snap: AppStateModel) -> tuple[str, str]:
    """Moon Phase astronomical calculation widget."""
    phase = get_moon_phase(datetime.now())
    return "Moon Phase:", f"{phase}".center(16)


def render_widget_uptime(snap: AppStateModel) -> tuple[str, str]:
    """System uptime and health diagnostic widget."""
    elapsed_sec = int(time.time() - START_TIME)
    hours = elapsed_sec // 3600
    minutes = (elapsed_sec % 3600) // 60
    wifi_str = "Offline" if snap.wifi_error else "Online"

    return f"Uptime: {hours}h {minutes}m", f"Wi-Fi: {wifi_str}"


def render_widget_settings(snap: AppStateModel) -> tuple[str, str]:
    """Scrollable row-based settings interface."""
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
    6: render_widget_moon,
    7: render_widget_uptime,
}