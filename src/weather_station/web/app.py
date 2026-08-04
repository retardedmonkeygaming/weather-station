import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from weather_station.core.state import state

app = FastAPI()

# FORCE ABSOLUTE PATHS
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "state": state})

@app.get("/api/data")
async def get_data():
    # This provides the live updates for the dashboard
    return {
        "indoor_temp": f"{state.indoor_temp:.1f}C" if state.indoor_temp else "N/A",
        "indoor_humid": f"{state.indoor_humid}%" if state.indoor_humid else "N/A",
        "outdoor_temp": f"{state.outdoor_temp}C",
        "outdoor_humid": f"{state.outdoor_humid}%",
        "wifi_status": "ONLINE" if not state.wifi_error else "OFFLINE",
        "dht_status": "ONLINE" if not state.dht_error else "ERROR"
    }