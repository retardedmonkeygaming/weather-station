import os
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.persistence.database import DatabaseManager
from weather_station.utils.formatting import calculate_moon_phase

app = FastAPI()
db = DatabaseManager()
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Helpers for the Dashboard
def format_temp_val(val):
    if val is None or val == "N/A": return "N/A"
    if settings.unit == "F": return f"{(float(val) * 9/5) + 32:.1f}F"
    return f"{float(val):.1f}C"

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "state": state, "format_temp": format_temp_val})

@app.get("/designer", response_class=HTMLResponse)
async def designer(request: Request):
    return templates.TemplateResponse("designer.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def web_settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "state": state, "settings": settings, "format_temp": format_temp_val})

@app.get("/logs", response_class=HTMLResponse)
async def view_logs(request: Request):
    # Literal restoration of the logs logic
    return templates.TemplateResponse("logs.html", {"request": request})

# API Endpoints - REWRITTEN TO MATCH YOUR EXACT JS CALLS
@app.get("/api/data")
async def get_live_data():
    from weather_station.services.system import SystemService
    stats = SystemService.get_stats()
    moon = calculate_moon_phase()
    return JSONResponse({
        "indoor_temp": format_temp_val(state.indoor_temp),
        "indoor_humid": f"{state.indoor_humid}%" if state.indoor_humid else "N/A",
        "outdoor_temp": format_temp_val(state.outdoor_temp),
        "outdoor_humid": f"{state.outdoor_humid}%" if state.outdoor_humid != "N/A" else "N/A",
        "aqi": state.aqi_val,
        "aqi_status": state.aqi_status,
        "uv_current": state.uv_index,
        "moon_phase": moon['short_name'],
        "moon_illumination": f"{moon['illumination']}%",
        "lcd_line1": state.last_line1,
        "lcd_line2": state.last_line2,
        "dht_status": "ONLINE" if not state.dht_error else "OFFLINE / ERROR",
        "wifi_status": "CONNECTED" if not state.wifi_error else "DISCONNECTED",
        "pi_cpu_temp": stats["cpu_temp"],
        "pi_cpu_usage": stats["cpu_usage"],
        "pi_ram_usage": stats["ram_usage"]
    })

@app.get("/api/pages")
async def get_pages():
    return JSONResponse(state.custom_pages)

@app.post("/api/save-page")
async def save_page(request: Request):
    body = await request.json()
    p_id, w_type = int(body.get("page_id", 1)), body.get("widget_type", "")
    state.custom_pages[p_id] = w_type
    await db.save_page_assignment(p_id, w_type)
    return JSONResponse({"status": "success"})

@app.post("/api/delete-page")
async def delete_page(request: Request):
    body = await request.json()
    p_id = int(body.get("page_id", 1))
    if p_id in state.custom_pages:
        del state.custom_pages[p_id]
    await db.delete_page_assignment(p_id)
    return JSONResponse({"status": "deleted"})

@app.post("/update-settings")
async def update_settings(
    unit: str = Form(...), buzzer: str = Form(...), screen: str = Form(...),
    auto_scroll: int = Form(...), alarm_on: str = Form(...),
    alarm_hr: int = Form(...), alarm_min: int = Form(...),
    api_rate: int = Form(...), log_rate: int = Form(...)
):
    settings.unit, settings.buzzer_mode = unit, buzzer
    await db.save_setting("unit", unit)
    await db.save_setting("buzzer", buzzer)
    return RedirectResponse(url="/settings", status_code=303)