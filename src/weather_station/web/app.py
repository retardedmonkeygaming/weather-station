from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from weather_station.core.state import state
from pathlib import Path

app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent

# Proper directory mounting
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "state": state})

@app.get("/api/data")
async def get_data():
    return {
        "lcd_line1": state.last_line1,
        "lcd_line2": state.last_line2,
        "indoor_temp": f"{state.indoor_temp:.1f}C" if state.indoor_temp else "N/A",
        "indoor_humid": f"{state.indoor_humid}%" if state.indoor_humid else "N/A",
        "outdoor_temp": f"{state.outdoor_temp}C",
        "dht_status": "ONLINE" if not state.dht_error else "OFFLINE",
        "wifi_status": "ONLINE" if not state.wifi_error else "OFFLINE"
    }

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from weather_station.persistence.database import DatabaseManager

db = DatabaseManager()

@app.post("/api/save-settings")
async def save_settings(
    unit: str = Form(...), 
    api_rate: int = Form(...),
    buzzer_mode: str = Form(...)
):
    # 1. Update the Database
    await db.save_setting("unit", unit)
    await db.save_setting("api_rate", str(api_rate))
    await db.save_setting("buzzer_mode", buzzer_mode)
    
    # 2. Update live config/state immediately
    from weather_station.core.config import settings
    settings.unit = unit
    settings.api_rate = api_rate
    settings.buzzer_mode = buzzer_mode
    
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/api/save-page")
async def save_page(page_id: int = Form(...), widget_type: str = Form(...)):
    # 1. Update Database
    await db.save_page_assignment(page_id, widget_type)
    
    # 2. Update Live State
    state.custom_pages[page_id] = widget_type
    
    return RedirectResponse(url="/designer", status_code=303)