from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from core.state import state
from persistence.database import save_setting
from utils.formatting import format_temp

router = APIRouter(prefix="/api")

@router.get("/data")
async def get_live_data():
    snap = state.get_snapshot_sync()
    return JSONResponse({
        "indoor_temp": format_temp(snap.indoor_temp, snap.temp_unit),
        "indoor_humid": f"{snap.indoor_humid:.1f}%" if snap.indoor_humid else "N/A",
        "outdoor_temp": format_temp(snap.outdoor_temp, snap.temp_unit),
        "outdoor_humid": f"{snap.outdoor_humid}%" if snap.outdoor_humid else "N/A",
        "outdoor_min": format_temp(snap.outdoor_min, snap.temp_unit),
        "outdoor_max": format_temp(snap.outdoor_max, snap.temp_unit),
        "uv_current": str(snap.uv_current),
        "uv_max": str(snap.uv_max),
        "aqi": snap.aqi_val,
        "aqi_status": snap.aqi_status,
        "pm2_5": snap.pm2_5_val,
        "pm10": snap.pm10_val,
        "dht_status": "OFFLINE" if snap.dht_error else "ONLINE",
        "wifi_status": "DISCONNECTED" if snap.wifi_error else "CONNECTED",
        "pi_cpu_temp": snap.pi_cpu_temp,
        "pi_cpu_usage": snap.pi_cpu_usage,
        "pi_ram_usage": snap.pi_ram_usage,
        "lcd_line1": snap.last_lcd_rendered_text[0],
        "lcd_line2": snap.last_lcd_rendered_text[1],
        "time": datetime.now().strftime("%H:%M:%S"),
        "date": datetime.now().strftime("%Y-%m-%d")
    })

@router.post("/save-page")
async def save_page(request: Request):
    body = await request.json()
    page_id = int(body.get("page_id", 1))
    widget_type = str(body.get("widget_type", ""))

    state.custom_lcd_pages[page_id] = widget_type
    if page_id > state._data.total_pages:
        await state.update(total_pages=page_id)

    await save_setting(f"custom_page_{page_id}", widget_type)
    return JSONResponse({"status": "success", "page_id": page_id, "widget": widget_type})

@router.post("/delete-page")
async def delete_page(request: Request):
    body = await request.json()
    page_id = int(body.get("page_id", 1))

    if page_id in state.custom_lcd_pages:
        del state.custom_lcd_pages[page_id]

    return JSONResponse({"status": "deleted", "page_id": page_id})