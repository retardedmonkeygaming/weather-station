"""Settings Route."""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from weather_station.core.state import state
from weather_station.persistence.database import save_setting
from weather_station.web.dependencies import templates

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
async def get_settings(request: Request):
    snap = state.get_snapshot_sync()
    return templates.TemplateResponse("settings.html", {"request": request, "state": snap})


@router.post("/settings")
async def update_settings(
    temp_unit: str = Form(...),
    buzzer_mode: str = Form(...),
    auto_scroll_speed: int = Form(...)
):
    await state.update(
        temp_unit=temp_unit,
        buzzer_mode=buzzer_mode,
        auto_scroll_speed=auto_scroll_speed
    )
    await save_setting("temp_unit", temp_unit)
    await save_setting("buzzer_mode", buzzer_mode)
    await save_setting("auto_scroll_speed", str(auto_scroll_speed))
    return RedirectResponse(url="/settings", status_code=303)