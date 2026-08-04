from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.persistence.database import DatabaseManager
from pathlib import Path

app = FastAPI()
db = DatabaseManager()
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "state": state})

@app.get("/designer", response_class=HTMLResponse)
async def designer(request: Request):
    return templates.TemplateResponse("designer.html", {"request": request, "state": state})

@app.get("/settings", response_class=HTMLResponse)
async def web_settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "state": state, "settings": settings})

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

@app.post("/api/save-settings")
async def save_settings(
    unit: str = Form(...), buzzer: str = Form(...), screen: str = Form(...),
    auto_scroll: int = Form(...), alarm_on: str = Form(...),
    alarm_hr: int = Form(...), alarm_min: int = Form(...),
    api_rate: int = Form(...), log_rate: int = Form(...)
):
    # Update Global Config
    settings.unit = unit
    settings.buzzer_mode = buzzer
    settings.api_rate = api_rate
    settings.log_rate = log_rate
    # Persistence
    await db.save_setting("unit", unit)
    await db.save_setting("buzzer", buzzer)
    await db.save_setting("api_rate", str(api_rate))
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/api/save-page")
async def save_page(request: Request):
    data = await request.json()
    p_id, w_type = int(data['page_id']), data['widget_type']
    state.custom_pages[p_id] = w_type
    await db.save_page_assignment(p_id, w_type)
    return {"status": "success"}