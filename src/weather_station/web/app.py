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

# ADD EMPTY ROUTES SO LINKS DON'T 404
@app.get("/designer")
async def designer_placeholder(request: Request):
    return "UI Designer Page - Coming in next update"

@app.get("/settings")
async def settings_placeholder(request: Request):
    return "Settings Page - Coming in next update"