"""API Endpoints for Telemetry, Settings, Page Visibility, and Webhooks."""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Dict
import json
from core.state import state
from persistence.database import save_setting, factory_reset_db, DB_FILE
import aiosqlite
from display.widgets import WIDGET_MAP, render_widget_settings

router = APIRouter(prefix="/api", tags=["api"])


class SettingsUpdateModel(BaseModel):
    temp_unit: str | None = None
    buzzer_mode: str | None = None
    log_interval: int | None = None
    api_fetch_interval: int | None = None
    temp_offset: float | None = None
    night_mode: bool | None = None
    enabled_pages: List[int] | None = None
    page_widget_map: Dict[int, int] | None = None
    high_temp_threshold: float | None = None
    low_temp_threshold: float | None = None
    webhook_url: str | None = None


@router.get("/data")
async def get_sensor_data():
    snap = await state.get_snapshot()
    return snap.model_dump()


@router.post("/settings")
async def update_settings(payload: SettingsUpdateModel):
    updates = {}
    
    mapping = {
        "temp_unit": payload.temp_unit,
        "buzzer_mode": payload.buzzer_mode,
        "log_interval": payload.log_interval,
        "api_fetch_interval": payload.api_fetch_interval,
        "temp_offset": payload.temp_offset,
        "night_mode": payload.night_mode,
        "high_temp_threshold": payload.high_temp_threshold,
        "low_temp_threshold": payload.low_temp_threshold,
        "webhook_url": payload.webhook_url,
    }

    for key, val in mapping.items():
        if val is not None:
            updates[key] = val
            await save_setting(key, val)

    if payload.enabled_pages is not None:
        updates["enabled_pages"] = payload.enabled_pages
        await save_setting("enabled_pages", ",".join(map(str, payload.enabled_pages)))

    if payload.page_widget_map is not None:
        updates["page_widget_map"] = payload.page_widget_map
        # persist as JSON string
        await save_setting("page_widget_map", json.dumps(payload.page_widget_map))

    await state.update(**updates)
    return {"status": "success", "updated": updates}


@router.get("/preview")
async def preview_widget(page: int | None = None, widget: int | None = None, mode: str | None = None):
    """Return two-line preview for a given page/widget or the settings menu when `mode=settings`."""
    snap = await state.get_snapshot()
    # Settings mode preview
    if mode == "settings":
        l1, l2 = render_widget_settings(snap)
        return {"lines": [l1, l2]}

    # explicit widget preview
    if widget is not None:
        fn = WIDGET_MAP.get(int(widget))
        if fn:
            l1, l2 = fn(snap)
            return {"lines": [l1, l2]}

    # page-based preview: consult page_widget_map if present
    if page is not None:
        # prefer state.page_widget_map if set
        mapping = getattr(snap, "page_widget_map", {}) or {}
        widget_id = mapping.get(int(page), int(page))
        fn = WIDGET_MAP.get(int(widget_id))
        if fn:
            l1, l2 = fn(snap)
            return {"lines": [l1, l2]}

    return {"lines": ["N/A","N/A"]}


@router.get("/history")
async def get_historical_logs(limit: int = Query(default=50, le=500)):
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
    await factory_reset_db()
    await state.update(
        temp_unit="C", buzzer_mode="ALL", log_interval=300,
        api_fetch_interval=600, temp_offset=0.0, night_mode=False,
        enabled_pages=[1, 2, 3, 4, 5, 6, 7],
        high_temp_threshold=35.0, low_temp_threshold=5.0, webhook_url=""
    )
    return {"status": "reset_complete"}