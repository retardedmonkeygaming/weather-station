"""API Endpoints for Telemetry, Settings, Page Visibility, and Logs."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any
from core.state import state
from persistence.database import save_setting, factory_reset_db, DB_FILE
import aiosqlite

router = APIRouter(prefix="/api", tags=["api"])


class SettingsUpdateModel(BaseModel):
    temp_unit: str | None = None
    buzzer_mode: str | None = None
    log_interval: int | None = None
    api_fetch_interval: int | None = None
    temp_offset: float | None = None
    night_mode: bool | None = None
    enabled_pages: List[int] | None = None


@router.get("/data")
async def get_sensor_data():
    """Returns current live application state snapshot."""
    snap = await state.get_snapshot()
    return snap.model_dump()


@router.post("/settings")
async def update_settings(payload: SettingsUpdateModel):
    """Updates system settings and persists changes instantly."""
    updates = {}
    if payload.temp_unit is not None:
        updates["temp_unit"] = payload.temp_unit
        await save_setting("temp_unit", payload.temp_unit)

    if payload.buzzer_mode is not None:
        updates["buzzer_mode"] = payload.buzzer_mode
        await save_setting("buzzer_mode", payload.buzzer_mode)

    if payload.log_interval is not None:
        updates["log_interval"] = payload.log_interval
        await save_setting("log_interval", payload.log_interval)

    if payload.api_fetch_interval is not None:
        updates["api_fetch_interval"] = payload.api_fetch_interval
        await save_setting("api_fetch_interval", payload.api_fetch_interval)

    if payload.temp_offset is not None:
        updates["temp_offset"] = payload.temp_offset
        await save_setting("temp_offset", payload.temp_offset)

    if payload.night_mode is not None:
        updates["night_mode"] = payload.night_mode
        await save_setting("night_mode", payload.night_mode)

    if payload.enabled_pages is not None:
        updates["enabled_pages"] = payload.enabled_pages
        await save_setting("enabled_pages", ",".join(map(str, payload.enabled_pages)))

    await state.update(**updates)
    return {"status": "success", "updated": updates}


@router.get("/history")
async def get_historical_logs(limit: int = Query(default=50, le=500)):
    """Returns historical database logs for Chart.js rendering."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT timestamp, indoor_temp, indoor_humid, outdoor_temp, outdoor_humid, uv_index, aqi FROM sensor_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in reversed(rows)]


@router.post("/reset")
async def reset_system_settings():
    """Factory reset settings endpoint."""
    await factory_reset_db()
    await state.update(
        temp_unit="C", buzzer_mode="ALL", log_interval=300,
        api_fetch_interval=600, temp_offset=0.0, night_mode=False,
        enabled_pages=[1, 2, 3, 4, 5, 6, 7]
    )
    return {"status": "reset_complete"}