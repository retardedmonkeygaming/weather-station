from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from weather_station.core.state import state

app = FastAPI()

# Mount static files and templates
# Note: On Mac, paths are relative to where you run the script
templates = Jinja2Templates(directory="src/weather_station/web/templates")

@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "state": state
    })

@app.get("/api/data")
async def get_data():
    return {
        "indoor_temp": state.indoor_temp,
        "indoor_humid": state.indoor_humid,
        "wifi_status": "OK" if not state.wifi_error else "ERROR"
    }