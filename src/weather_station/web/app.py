import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse

from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.persistence.database import DatabaseManager
from weather_station.utils.formatting import calculate_moon_phase, get_comfort_level

app = FastAPI()
db = DatabaseManager()

# --- REPLICATING YOUR ORIGINAL HELPER FUNCTIONS FOR THE UI ---
def get_nav_header():
    return """
    <div style="margin-bottom: 20px; background: #0288d1; padding: 12px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <a href="/" style="margin-right: 20px; text-decoration: none; color: white; font-weight: bold; font-size: 16px;">Dashboard</a>
        <a href="/designer" style="margin-right: 20px; text-decoration: none; color: white; font-weight: bold; font-size: 16px;">UI Designer</a>
        <a href="/logs" style="margin-right: 20px; text-decoration: none; color: white; font-weight: bold; font-size: 16px;">System Logs</a>
        <a href="/settings" style="text-decoration: none; color: white; font-weight: bold; font-size: 16px;">Settings & Calibration</a>
    </div>
    """

def format_temp_ui(val):
    if val is None or val == "N/A": return "N/A"
    try:
        v = float(val)
        if settings.unit == "F": return f"{(v * 9/5) + 32:.1f}F"
        return f"{v:.1f}C"
    except: return "N/A"

# --- DASHBOARD ROUTE (LITERAL FROM ORIGINAL) ---
@app.get("/", response_class=HTMLResponse)
async def web_dashboard():
    logs_data = []
    try:
        async with db.get_connection() as conn:
            async with conn.execute("SELECT timestamp, in_temp, in_humid, out_temp, out_humid FROM weather_logs ORDER BY id DESC LIMIT 15") as cursor:
                logs_data = await cursor.fetchall()
    except: pass

    rows_html = "".join([
        f"<tr><td>{r[0]}</td><td>{r[1]} C</td><td>{r[2]}%</td><td>{r[3]} C</td><td>{r[4]}%</td></tr>"
        for r in logs_data
    ])
    
    p = calculate_moon_phase()
    html_content = f"""
    <!DOCTYPE html><html><head><title>Weather Dashboard</title><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f7f6; color: #333; }} h1 {{ color: #0288d1; }} .card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }} table {{ width: 100%; border-collapse: collapse; background: white; }} th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }} th {{ background-color: #0288d1; color: white; }}</style>
    </head><body><h1>Weather Station Dashboard</h1>{get_nav_header()}
    <div class="card"><h2>Current Live Metrics</h2>
    <p><strong>Indoor Temp:</strong> {format_temp_ui(state.indoor_temp)} | <strong>Indoor Humidity:</strong> {state.indoor_humid}%</p>
    <p><strong>Outdoor Temp:</strong> {format_temp_ui(state.outdoor_temp)} | <strong>Outdoor Humidity:</strong> {state.outdoor_humid}%</p>
    <p><strong>AQI:</strong> {state.aqi_val} ({state.aqi_status}) | <strong>UV Index:</strong> {state.uv_index}</p>
    <p><strong>Moon Phase:</strong> 🌙 {p['short_name']} ({p['illumination']}% Illumination)</p>
    </div><h2>Recent History</h2><table><tr><th>Timestamp</th><th>Indoor Temp</th><th>Indoor Humid</th><th>Outdoor Temp</th><th>Outdoor Humidity</th></tr>{rows_html}</table>
    </body></html>"""
    return html_content

# --- DESIGNER ROUTE (LITERAL FROM ORIGINAL) ---
@app.get("/designer", response_class=HTMLResponse)
async def ui_designer():
    html_content = f"""
    <!DOCTYPE html><html><head><title>LCD Designer</title><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 20px; background-color: #eceff1; color: #37474f; }} h1 {{ color: #0288d1; }} .guide-banner {{ background: #e3f2fd; border: 1px solid #90caf9; color: #0d47a1; padding: 12px 18px; border-radius: 8px; margin-bottom: 20px; }} .page-selector {{ display: flex; align-items: center; gap: 10px; background: white; padding: 14px; border-radius: 8px; margin-bottom: 20px; }} .page-btn {{ padding: 8px 16px; background: #cfd8dc; border-radius: 20px; cursor: pointer; border: none; }} .page-btn.active {{ background: #0288d1; color: white; }} .grid-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }} .widget-card {{ background: white; border: 2px solid #b0bec5; border-radius: 10px; padding: 16px; text-align: center; cursor: pointer; }} .widget-card.selected {{ border-color: #2e7d32; background-color: #e8f5e9; }} .lcd-preview-card {{ background: #1b2a1a; color: #33ff33; font-family: 'Courier New', monospace; padding: 15px; border-radius: 8px; border: 4px solid #2e4d2a; font-size: 18px; white-space: pre; display:inline-block; }} .btn {{ padding: 12px 20px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; color: white; }} .btn-save {{ background-color: #2e7d32; }}</style>
    </head><body><h1>LCD Screen Designer</h1>{get_nav_header()}
    <div class="guide-banner">🎯 <strong>How it works:</strong> Pick a tab, click a card, hit <strong>Apply</strong>!</div>
    <div class="page-selector"><strong>Select Page:</strong> <div id="page-tabs" style="display:flex; gap:8px;"></div><button class="page-btn" onclick="addPage()">+ Add Page</button></div>
    <div class="grid-container">
        <div class="widget-card" id="card_widget_indoor" onclick="selectWidget('widget_indoor')">🌡️<br>Indoor Climate</div>
        <div class="widget-card" id="card_widget_outdoor" onclick="selectWidget('widget_outdoor')">☀️<br>Outdoor Weather</div>
        <div class="widget-card" id="card_widget_moon" onclick="selectWidget('widget_moon')">🌙<br>Moon Phase</div>
        <div class="widget-card" id="card_widget_clock" onclick="selectWidget('widget_clock')">🕒<br>Clock</div>
    </div>
    <div style="margin-top:25px;"><h3>LCD Preview:</h3><div class="lcd-preview-card" id="lcd-preview">Loading..</div></div>
    <button class="btn btn-save" onclick="savePageAssignment()" style="margin-top:20px;">💾 Apply & Save to LCD</button>
    <script>
        let activePage = 1; let totalPages = 6; let selectedWidgetType = "";
        function renderTabs() {{ let c = document.getElementById("page-tabs"); c.innerHTML = ""; for (let i = 1; i <= totalPages; i++) {{ let b = document.createElement("button"); b.className = "page-btn" + (i === activePage ? " active" : ""); b.innerText = "Page " + i; b.onclick = () => switchPage(i); c.appendChild(b); }} }}
        function switchPage(p) {{ activePage = p; renderTabs(); }}
        function selectWidget(w) {{ selectedWidgetType = w; document.querySelectorAll(".widget-card").forEach(c => c.classList.remove("selected")); document.getElementById("card_" + w).classList.add("selected"); }}
        async function savePageAssignment() {{ await fetch('/api/save-page', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ page_id: activePage, widget_type: selectedWidgetType }}) }}); alert("Saved!"); }}
        setInterval(async () => {{ const res = await fetch('/api/data'); const d = await res.json(); document.getElementById("lcd-preview").innerText = d.lcd_line1 + "\\n" + d.lcd_line2; }}, 1000);
        renderTabs();
    </script></body></html>"""
    return html_content

# --- API ENDPOINTS (LITERAL FROM ORIGINAL) ---
@app.get("/api/data")
async def get_live_data():
    from weather_station.services.system import SystemService
    stats = SystemService.get_stats()
    return {
        "lcd_line1": state.last_line1,
        "lcd_line2": state.last_line2,
        "indoor_temp": format_temp_ui(state.indoor_temp),
        "indoor_humid": state.indoor_humid,
        "outdoor_temp": format_temp_ui(state.outdoor_temp),
        "outdoor_humid": state.outdoor_humid,
        "aqi": state.aqi_val,
        "aqi_status": state.aqi_status,
        "pi_cpu_temp": stats["cpu_temp"]
    }

@app.post("/api/save-page")
async def save_page(request: Request):
    body = await request.json()
    p_id, w_type = int(body.get("page_id", 1)), body.get("widget_type", "")
    state.custom_pages[p_id] = w_type
    await db.save_page_assignment(p_id, w_type)
    return {"status": "success"}