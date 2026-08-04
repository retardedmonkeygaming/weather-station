from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.persistence.database import DatabaseManager
from weather_station.utils.formatting import calculate_moon_phase

app = FastAPI()
db = DatabaseManager()

def get_nav_header():
    return """
    <div style="margin-bottom: 20px; background: #0288d1; padding: 12px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <a href="/" style="margin-right: 20px; text-decoration: none; color: white; font-weight: bold; font-size: 16px;">Dashboard</a>
        <a href="/designer" style="margin-right: 20px; text-decoration: none; color: white; font-weight: bold; font-size: 16px;">UI Designer</a>
        <a href="/logs" style="margin-right: 20px; text-decoration: none; color: white; font-weight: bold; font-size: 16px;">System Logs</a>
        <a href="/settings" style="text-decoration: none; color: white; font-weight: bold; font-size: 16px;">Settings & Calibration</a>
    </div>
    """

@app.get("/", response_class=HTMLResponse)
async def web_dashboard():
    logs = await db.get_logs(15)
    rows_html = "".join([f"<tr><td>{r[0]}</td><td>{r[1]} C</td><td>{r[2]}%</td><td>{r[3]} C</td><td>{r[4]}%</td></tr>" for r in logs])
    p = calculate_moon_phase()
    return f"""
    <!DOCTYPE html><html><head><title>Weather Dashboard</title><style>body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f7f6; }} h1 {{ color: #0288d1; }} .card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }} table {{ width: 100%; border-collapse: collapse; background: white; }} th, td {{ padding: 10px; border: 1px solid #ddd; }} th {{ background-color: #0288d1; color: white; }}</style></head>
    <body><h1>Weather Station Dashboard</h1>{get_nav_header()}
    <div class="card"><h2>Current Live Metrics</h2><p><strong>Indoor Temp:</strong> {state.indoor_temp}C | <strong>Humidity:</strong> {state.indoor_humid}%</p><p><strong>Outdoor Temp:</strong> {state.outdoor_temp}C | <strong>AQI:</strong> {state.aqi_val}</p><p><strong>Moon Phase:</strong> 🌙 {p['short_name']} ({p['illumination']}% Illumination)</p></div>
    <h2>Recent History</h2><table><tr><th>Timestamp</th><th>Indoor Temp</th><th>Indoor Humid</th><th>Outdoor Temp</th><th>Outdoor Humid</th></tr>{rows_html}</table></body></html>"""

@app.get("/designer", response_class=HTMLResponse)
async def ui_designer():
    return f"""
    <!DOCTYPE html><html><head><title>LCD Designer</title><style>body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 20px; background-color: #eceff1; }} h1 {{ color: #0288d1; }} .guide-banner {{ background: #e3f2fd; border: 1px solid #90caf9; padding: 12px; border-radius: 8px; margin-bottom: 20px; }} .page-selector {{ display: flex; align-items: center; gap: 10px; background: white; padding: 14px; border-radius: 8px; margin-bottom: 20px; }} .page-btn {{ padding: 8px 16px; background: #cfd8dc; border-radius: 20px; cursor: pointer; border: none; }} .page-btn.active {{ background: #0288d1; color: white; }} .grid-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }} .widget-card {{ background: white; border: 2px solid #b0bec5; border-radius: 10px; padding: 16px; text-align: center; cursor: pointer; }} .widget-card.selected {{ border-color: #2e7d32; background-color: #e8f5e9; }} .lcd-preview-card {{ background: #1b2a1a; color: #33ff33; font-family: 'Courier New', monospace; padding: 15px; border-radius: 8px; font-size: 18px; white-space: pre; display:inline-block; }}</style></head>
    <body><h1>LCD Screen Designer (1 Page = 1 Widget)</h1>{get_nav_header()}
    <div class="guide-banner">🎯 Pick a Page tab, click a Widget card, hit Apply!</div>
    <div class="page-selector"><strong>Select Page:</strong><div id="page-tabs" style="display:flex; gap:8px;"></div><button class="page-btn" onclick="addPage()" style="background:#0288d1; color:white;">+ Add Page</button></div>
    <div class="grid-container">
        <div class="widget-card" id="card_widget_indoor" onclick="selectWidget('widget_indoor')">🌡️<br>Indoor Climate</div><div class="widget-card" id="card_widget_outdoor" onclick="selectWidget('widget_outdoor')">☀️<br>Outdoor Weather</div><div class="widget-card" id="card_widget_moon" onclick="selectWidget('widget_moon')">🌙<br>Moon Phase</div><div class="widget-card" id="card_widget_aqi" onclick="selectWidget('widget_aqi')">🍃<br>Air Quality</div><div class="widget-card" id="card_widget_pi" onclick="selectWidget('widget_pi')">🤖<br>Pi System</div><div class="widget-card" id="card_widget_clock" onclick="selectWidget('widget_clock')">🕒<br>Clock</div><div class="widget-card" id="card_widget_humidity" onclick="selectWidget('widget_humidity')">💧<br>Humidity</div><div class="widget-card" id="card_widget_uv" onclick="selectWidget('widget_uv')">☀️<br>UV Index</div><div class="widget-card" id="card_widget_pm" onclick="selectWidget('widget_pm')">🌫️<br>Pollutants</div><div class="widget-card" id="card_widget_forecast" onclick="selectWidget('widget_forecast')">📅<br>Temp Range</div><div class="widget-card" id="card_widget_comfort" onclick="selectWidget('widget_comfort')">😊<br>Comfort</div><div class="widget-card" id="card_widget_status" onclick="selectWidget('widget_status')">⚡<br>Diagnostics</div>
    </div>
    <div style="margin-top:25px;"><h3>LCD Preview:</h3><div class="lcd-preview-card" id="lcd-preview">Loading..</div></div>
    <div style="margin-top:20px;"><button onclick="savePageAssignment()" style="background:#2e7d32; color:white; padding:12px 24px; border:none; border-radius:5px; cursor:pointer;">💾 Apply & Save to LCD</button> <button onclick="resetPage()" style="background:#ed6c02; color:white; padding:12px 24px; border:none; border-radius:5px;">🔄 Reset</button> <button onclick="deletePage()" style="background:#c62828; color:white; padding:12px 24px; border:none; border-radius:5px;">🗑️ Delete</button></div>
    <script>
        let activePage = 1; let totalPages = 6; let selectedWidgetType = "";
        function renderTabs() {{ let c = document.getElementById("page-tabs"); c.innerHTML = ""; for (let i = 1; i <= totalPages; i++) {{ let b = document.createElement("button"); b.className = "page-btn" + (i === activePage ? " active" : ""); b.innerText = "Page " + i; b.onclick = () => switchPage(i); c.appendChild(b); }} }}
        function switchPage(p) {{ activePage = p; renderTabs(); }}
        function addPage() {{ if(totalPages<10) totalPages++; renderTabs(); }}
        function selectWidget(w) {{ selectedWidgetType = w; document.querySelectorAll(".widget-card").forEach(c => c.classList.remove("selected")); document.getElementById("card_" + w).classList.add("selected"); }}
        async function savePageAssignment() {{ await fetch('/api/save-page', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ page_id: activePage, widget_type: selectedWidgetType }}) }}); alert("Saved!"); }}
        async function resetPage() {{ selectedWidgetType="widget_clock"; await savePageAssignment(); }}
        async function deletePage() {{ if(activePage > 6) {{ await fetch('/api/delete-page', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ page_id: activePage }}) }}); location.reload(); }} }}
        setInterval(async () => {{ const res = await fetch('/api/data'); const d = await res.json(); document.getElementById("lcd-preview").innerText = d.lcd_line1 + "\\n" + d.lcd_line2; }}, 1000);
        renderTabs();
    </script></body></html>"""

@app.get("/logs", response_class=HTMLResponse)
async def view_logs():
    logs = await db.get_logs(100)
    total = await db.get_total_logs()
    rows_html = "".join([f"<tr><td>#{i+1}</td><td>{r[0]}</td><td>{r[1]} C</td><td>{r[2]}%</td><td>{r[3]} C</td><td>{r[4]}%</td></tr>" for i, r in enumerate(logs)])
    return f"""<!DOCTYPE html><html><head><title>Logs</title><style>body {{ font-family: Arial; margin: 20px; background-color: #f4f7f6; }} h1 {{ color: #0288d1; }} table {{ width: 100%; border-collapse: collapse; background: white; }} th, td {{ padding: 10px; border: 1px solid #ddd; }} th {{ background-color: #0288d1; color: white; }}</style></head>
    <body><h1>System Logs</h1>{get_nav_header()}<div><strong>Total Entries:</strong> {total}</div><table><tr><th>ID</th><th>Timestamp</th><th>Indoor T</th><th>Indoor H</th><th>Outdoor T</th><th>Outdoor H</th></tr>{rows_html}</table></body></html>"""

@app.get("/settings", response_class=HTMLResponse)
async def web_settings():
    return f"""<!DOCTYPE html><html><head><title>Settings</title><style>body {{ font-family: Arial; margin: 20px; background-color: #f4f7f6; }} h1 {{ color: #0288d1; }} .card {{ background: white; padding: 20px; border-radius: 8px; }} .form-group {{ margin-bottom: 15px; }} input, select {{ width: 100%; padding: 10px; }}</style></head>
    <body><h1>System Settings</h1>{get_nav_header()}
    <div class="card"><form action="/update-settings" method="post">
    <div class="form-group"><label>Unit:</label><select name="unit"><option value="C" {"selected" if settings.unit=="C" else ""}>Celsius</option><option value="F" {"selected" if settings.unit=="F" else ""}>Fahrenheit</option></select></div>
    <div class="form-group"><label>Buzzer:</label><select name="buzzer"><option value="ALL">ALL</option><option value="MUTE">MUTE</option></select></div>
    <div class="form-group"><label>Alarm HR (0-23):</label><input type="number" name="alarm_hr" value="17"></div>
    <div class="form-group"><label>Alarm MIN (0-59):</label><input type="number" name="alarm_min" value="0"></div>
    <input type="submit" value="Save Settings" style="background:#0288d1; color:white; border:none; padding:10px; cursor:pointer; width:100%;">
    </form></div></body></html>"""

@app.get("/api/data")
async def get_live_data():
    return {"lcd_line1": state.last_line1, "lcd_line2": state.last_line2, "indoor_temp": state.indoor_temp, "indoor_humid": state.indoor_humid, "outdoor_temp": state.outdoor_temp, "aqi_val": state.aqi_val}

@app.post("/api/save-page")
async def save_page(request: Request):
    body = await request.json()
    p_id, w_type = int(body.get("page_id", 1)), body.get("widget_type", "")
    state.custom_pages[p_id] = w_type
    await db.save_page_assignment(p_id, w_type)
    return {"status": "success"}

@app.post("/api/delete-page")
async def delete_page(request: Request):
    body = await request.json()
    p_id = int(body.get("page_id", 1))
    if p_id in state.custom_pages: del state.custom_pages[p_id]
    await db.delete_page_assignment(p_id)
    return {"status": "deleted"}

@app.post("/update-settings")
async def update_settings(unit: str = Form(...), buzzer: str = Form(...), alarm_hr: int = Form(...), alarm_min: int = Form(...)):
    settings.unit, settings.buzzer_mode = unit, buzzer
    await db.save_setting("unit", unit)
    await db.save_setting("buzzer", buzzer)
    return RedirectResponse(url="/settings", status_code=303)