"""UI Designer View Route."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from weather_station.core.state import state
from weather_station.web.dependencies import templates

router = APIRouter()


@router.get("/designer", response_class=HTMLResponse)
async def get_designer(request: Request):
    snap = state.get_snapshot_sync()
    return templates.TemplateResponse("designer.html", {"request": request, "state": snap})