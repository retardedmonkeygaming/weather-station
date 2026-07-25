import aiosqlite
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from persistence.database import DB_FILE
from web.dependencies import templates

router = APIRouter()

@router.get("/logs", response_class=HTMLResponse)
async def get_logs(request: Request):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT timestamp, indoor_temp, indoor_humid, outdoor_temp, outdoor_humid, uv_index, aqi FROM sensor_logs ORDER BY id DESC LIMIT 50") as cursor:
            rows = await cursor.fetchall()

    return templates.TemplateResponse("logs.html", {"request": request, "logs": rows})