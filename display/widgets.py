"""LCD 16x2 Text Rendering Widgets."""
from datetime import datetime
from core.state import AppStateModel
from utils.formatting import format_temp

HOURGLASS_FRAMES = ["⌛", "⏳"]

def render_widget_clock(snap: AppStateModel) -> tuple[str, str]:
    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")
    
    # Animated clock frame toggle
    frame_char = HOURGLASS_FRAMES[now.second % 2]
    line1 = f"{frame_char} {time_str}".center(16)
    
    alarm_char = "🔔" if snap.alarm_enabled else "  "
    line2 = f"{date_str} {alarm_char}".center(16)
    
    return line1, line2

def render_widget_indoor(snap: AppStateModel) -> tuple[str, str]:
    t_str = format_temp(snap.indoor_temp, snap.temp_unit)
    h_str = f"{snap.indoor_humid:.0f}%" if snap.indoor_humid is not None else "N/A"
    
    # Short comfort status rating
    comfort = "OK"
    if snap.indoor_temp is not None:
        if snap.indoor_temp > 28: comfort = "Hot! :("
        elif snap.indoor_temp < 18: comfort = "Cold! :("
        else: comfort = "Comfort :)"
        
    return f"In:{t_str} H:{h_str}", f"State:{comfort}"

def render_widget_outdoor(snap: AppStateModel) -> tuple[str, str]:
    t_str = format_temp(snap.outdoor_temp, snap.temp_unit)
    h_str = f"{snap.outdoor_humid}%" if snap.outdoor_humid is not None else "N/A"
    return f"Out:{t_str}", f"Humid:{h_str} UV:{snap.uv_current or 'N/A'}"

def render_widget_aqi(snap: AppStateModel) -> tuple[str, str]:
    return f"AQI:{snap.aqi_val} ({snap.aqi_status[:4]})", f"P2.5:{snap.pm2_5_val} P10:{snap.pm10_val}"

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