from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from weather_station.core.state import state
from weather_station.core.config import settings
from pathlib import Path

app = FastAPI()
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
        "outdoor_temp": f"{state.outdoor_temp}C"
    }