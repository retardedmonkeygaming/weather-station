from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from core.state import state
from web.dependencies import templates

router = APIRouter()

@router.get("/designer", response_class=HTMLResponse)
async def get_designer(request: Request):
    snap = state.get_snapshot_sync()
    return templates.TemplateResponse("designer.html", {"request": request, "state": snap})