from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from core.state import state
from web.dependencies import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    snap = state.get_snapshot_sync()
    return templates.TemplateResponse("dashboard.html", {"request": request, "state": snap})