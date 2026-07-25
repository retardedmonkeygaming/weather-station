"""Dashboard View Route."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from weather_station.core.state import state
from weather_station.web.dependencies import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    snap = state.get_snapshot_sync()
    return templates.TemplateResponse("dashboard.html", {"request": request, "state": snap})