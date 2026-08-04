import os
from pathlib import Path
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

def format_temp_ui(val):
    if val is None or val == "N/A": return "N/A"
    try:
        v = float(val)
        if settings.unit == "F": return f"{(v * 9/5) + 32:.1f}F"
        return f"{v:.1f}C"
    except: return "N/A"

@app.get("/", response_class=HTMLResponse)
async def web_dashboard():
    logs = await db.get_logs(15)
    rows_html = "".join([f"<tr><td>{r[0]}</td><td>{r[1]} C</td><td>{r[2]}%</td><td>{r[3]} C</td><td>{r[4]}%</td></tr>" for r in logs])
    p = calculate_moon_phase()
    return f"""
    <!DOCTYPE html><html><head><title>Weather Dashboard</title><style>body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f7f6; }} h1 {{ color: #0288d1; }} .card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }} table {{ width: 100%; border-collapse: collapse; background: white; }} th, td {{ padding: 10px; border: 1px solid #ddd; }} th {{ background-color: #0288d1; color: white; }}</style></head>
    <body><h1>Weather Station Dashboard</h1>{get_nav_header()}
    <div class="card"><h2>Current Live Metrics</h2><p><strong>Indoor Temp:</strong> {format_temp_ui(state.indoor_temp)} | <strong>Humidity:</strong> {state.indoor_humid}%</p><p><strong>Outdoor Temp:</strong> {format_temp_ui(state.outdoor_temp)} | <strong>AQI:</strong> {state.aqi_val}</p><p><strong>Moon Phase:</strong> 🌙 {p['short_name']} ({p['illumination']}% Illumination)</p></div>
    <h2>Recent History</h2><table><tr><th>Timestamp</th><th>Indoor Temp</th><th>Indoor Humid</th><th>Outdoor Temp</th><th>Outdoor Humid</th></tr>{rows_html}</table></body></html>"""

@app.get("/designer", response_class=HTMLResponse)
async def ui_designer():
    return f"""
    <!DOCTYPE html><html><head><title>LCD Designer</title><style>body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 20px; background-color: #eceff1; color: #37474f; }} h1 {{ color: #0288d1; }} .guide-banner {{ background: #e3f2fd; border: 1px solid #90caf9; padding: 12px; border-radius: 8px; margin-bottom: 20px; }} .page-selector {{ display: flex; align-items: center; gap: 10px; background: white; padding: 14px; border-radius: 8px; margin-bottom: 20px; }} .page-btn {{ padding: 8px 16px; background: #cfd8dc; border-radius: 20px; cursor: pointer; border: none; }} .page-btn.active {{ background: #0288d1; color: white; }} .grid-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }} .widget-card {{ background: white; border: 2px solid #b0bec5; border-radius: 10px; padding: 16px; text-align: center; cursor: pointer; }} .widget-card.selected {{ border-color: #2e7d32; background-color: #e8f5e9; }} .lcd-preview-card {{ background: #1b2a1a; color: #33ff33; font-family: 'Courier New', monospace; padding: 15px; border-radius: 8px; font-size: 18px; white-space: pre; display:inline-block; }}</style></head>
    <body><h1>LCD Screen Designer (1 Page = 1 Widget)</h1>{get_nav_header()}
    <div class="guide-banner">🎯 Pick a Page tab, click a Widget card, hit Apply!</div>
    <div class="page-selector"><strong>Select Page:</strong><div id="page-tabs" style="display:flex; gap:8px;"></div><button class="page-btn" onclick="addPage()" style="background:#0288d1; color:white;">+ Add Page</button></div>
    <div class="grid-container">
        <div class="widget-card" id="card_widget_indoor" onclick="selectWidget('widget_indoor')">🌡️<br>Indoor Climate</div><div class="widget-card" id="card_widget_outdoor" onclick="selectWidget('widget_outdoor')">☀️<br>Outdoor Weather</div><div class="widget-card" id="card_widget_moon" onclick="selectWidget('widget_moon')">🌙<br>Moon Phase</div><div class="widget-card" id="card_widget_aqi" onclick="selectWidget('widget_aqi')">🍃<br>Air Quality</div><div class="widget-card" id="card_widget_pi" onclick="selectWidget('widget_pi')">🤖<br>Pi System</div><div class="widget-card" id="card_widget_clock" onclick="selectWidget('widget_clock')">🕒<br>Clock</div><div class="widget-card" id="card_widget_humidity" onclick="selectWidget('widget_humidity')">💧<br>Humidity</div><div class="widget-card" id="card_widget_uv" onclick="selectWidget('widget_uv')">☀️<br>UV Index</div><div class="widget-card" id="card_widget_pm" onclick="selectWidget('widget_pm')">🌫️<br>Pollutants</div><div class="widget-card" id="card_widget_forecast" onclick="selectWidget('widget_forecast')">📅<br>Temp Range</div><div class="widget-card" id="card_widget_comfort" onclick="selectWidget('widget_comfort')">😊<br>Comfort</div><div class="widget-card" id="card_widget_status" onclick="selectWidget('widget_status')">⚡<br>Diagnostics</div>
    </div>
    <div style="margin-top:25px;"><h3>LCD Preview:</h3><div class="lcd-preview-card" id="lcd-preview">Loading..</div></div>
    <div style="margin-top:20px;"><button onclick="savePageAssignment()" style="background:#2e7d32; color:white; padding:12px 24px; border:none; border-radius:5px; cursor:pointer;">💾 Apply & Save to LCD</button></div>
    <script>
        let activePage = 1; let totalPages = 6; let selectedWidgetType = "";
        function renderTabs() {{ let c = document.getElementById("page-tabs"); c.innerHTML = ""; for (let i = 1; i <= totalPages; i++) {{ let b = document.createElement("button"); b.className = "page-btn" + (i === activePage ? " active" : ""); b.innerText = "Page " + i; b.onclick = () => switchPage(i); c.appendChild(b); }} }}
        function switchPage(p) {{ activePage = p; renderTabs(); }}
        function addPage() {{ if(totalPages<10) totalPages++; renderTabs(); }}
        function selectWidget(w) {{ selectedWidgetType = w; document.querySelectorAll(".widget-card").forEach(c => c.classList.remove("selected")); document.getElementById("card_" + w).classList.add("selected"); }}
        async function savePageAssignment() {{ await fetch('/api/save-page', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ page_id: activePage, widget_type: selectedWidgetType }}) }}); alert("Saved!"); }}
        setInterval(async () => {{ const res = await fetch('/api/data'); const d = await res.json(); document.getElementById("lcd-preview").innerText = d.lcd_line1 + "\\n" + d.lcd_line2; }}, 1000);
        renderTabs();
    </script></body></html>"""

@app.get("/settings", response_class=HTMLResponse)
async def web_settings():
    return f"""
    <!DOCTYPE html><html><head><title>Weather Station Settings</title><style>body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f7f6; color: #333; }} h1 {{ color: #0288d1; }} .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; max-width: 600px; }} .form-group {{ margin-bottom: 15px; }} label {{ display: block; font-weight: bold; margin-bottom: 5px; }} select, input {{ width: 100%; padding: 10px; border-radius: 4px; border: 1px solid #ccc; box-sizing: border-box; }} .btn-save {{ background-color: #0288d1; color: white; border: none; font-weight: bold; cursor: pointer; margin-top: 10px; }} .btn-calibrate {{ background-color: #388e3c; color: white; border: none; padding: 10px; width: 100%; font-weight: bold; cursor: pointer; margin-top: 10px; border-radius: 4px; }}</style></head>
    <body><h1>System Settings & Calibration</h1>{get_nav_header()}
    <div class="card"><h2>Location Settings</h2><form action="/update-location" method="post"><div class="form-group"><label>Latitude:</label><input type="text" name="latitude" value="{settings.latitude}"></div><div class="form-group"><label>Longitude:</label><input type="text" name="longitude" value="{settings.longitude}"></div><input type="submit" value="Update Location" class="btn-save"></form></div>
    <div class="card"><h2>DHT11 Auto-Calibration</h2><p><strong>Offset:</strong> {settings.dht_temp_offset:+.1f} C</p><p><strong>Outdoor API Temp:</strong> {format_temp_ui(state.outdoor_temp)}</p><form action="/calibrate-dht" method="post"><button type="submit" class="btn-calibrate">Auto-Calibrate Sensor Against Outdoor API</button></form><form action="/reset-dht" method="post"><button type="submit" style="background:#757575; color:white; border:none; padding:10px; width:100%; margin-top:10px; border-radius:4px; cursor:pointer;">Reset Calibration (0.0C)</button></form></div>
    <div class="card"><h2>Device Preferences</h2><form action="/update-settings" method="post">
    <div class="form-group"><label>Temperature Unit:</label><select name="unit"><option value="C" {"selected" if settings.unit=="C" else ""}>Celsius</option><option value="F" {"selected" if settings.unit=="F" else ""}>Fahrenheit</option></select></div>
    <div class="form-group"><label>Buzzer Mode:</label><select name="buzzer"><option value="ALL" {"selected" if settings.buzzer_mode=="ALL" else ""}>ALL</option><option value="MUTE" {"selected" if settings.buzzer_mode=="MUTE" else ""}>MUTE</option></select></div>
    <div class="form-group"><label>Daily Alarm:</label><select name="alarm_on"><option value="OFF">OFF</option><option value="ON">ON</option></select></div>
    <div class="form-group"><label>Alarm Time:</label><div style="display:flex; gap:10px;"><input type="number" name="alarm_hr" value="17"><input type="number" name="alarm_min" value="0"></div></div>
    <div class="form-group"><label>API Interval (Mins):</label><input type="number" name="api_rate" value="{settings.api_rate}"></div>
    <div class="form-group"><label>Log Interval (Mins):</label><input type="number" name="log_rate" value="{settings.log_rate}"></div>
    <input type="submit" value="Save All Settings" class="btn-save"></form></div>
    </body></html>"""

@app.get("/logs", response_class=HTMLResponse)
async def view_logs():
    logs = await db.get_logs(100)
    total = await db.get_total_logs()
    rows_html = "".join([f"<tr><td>#{i+1}</td><td>{r[0]}</td><td>{r[1]} C</td><td>{r[2]}%</td><td>{r[3]} C</td><td>{r[4]}%</td></tr>" for i, r in enumerate(logs)])
    return f"<!DOCTYPE html><html><head><title>Logs</title><style>body {{ font-family: Arial; margin: 20px; background-color: #f4f7f6; }} h1 {{ color: #0288d1; }} table {{ width: 100%; border-collapse: collapse; background: white; }} th, td {{ padding: 10px; border: 1px solid #ddd; }} th {{ background-color: #0288d1; color: white; }}</style></head><body><h1>System Logs</h1>{get_nav_header()}<div><strong>Total Entries:</strong> {total}</div><table><tr><th>ID</th><th>Timestamp</th><th>Indoor T</th><th>Indoor H</th><th>Outdoor T</th><th>Outdoor H</th></tr>{rows_html}</table></body></html>"

@app.get("/api/data")
async def get_live_data():
    return {"lcd_line1": state.last_line1, "lcd_line2": state.last_line2, "indoor_temp": format_temp_ui(state.indoor_temp), "indoor_humid": state.indoor_humid, "outdoor_temp": format_temp_ui(state.outdoor_temp), "aqi_val": state.aqi_val}

@app.post("/api/save-page")
async def save_page(request: Request):
    body = await request.json()
    p_id, w_type = int(body.get("page_id", 1)), body.get("widget_type", "")
    state.custom_pages[p_id] = w_type
    await db.save_page_assignment(p_id, w_type)
    return {"status": "success"}

@app.post("/update-location")
async def update_location(latitude: str = Form(...), longitude: str = Form(...)):
    settings.latitude, settings.longitude = latitude, longitude
    await db.save_setting("latitude", latitude)
    await db.save_setting("longitude", longitude)
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/calibrate-dht")
async def calibrate_dht():
    if state.indoor_temp_raw and state.outdoor_temp != "N/A":
        settings.dht_temp_offset = round(float(state.outdoor_temp) - state.indoor_temp_raw, 1)
        await db.save_setting("dht_temp_offset", str(settings.dht_temp_offset))
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/reset-dht")
async def reset_dht():
    settings.dht_temp_offset = 0.0
    await db.save_setting("dht_temp_offset", "0.0")
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/update-settings")
async def update_settings(unit: str = Form(...), buzzer: str = Form(...), alarm_hr: int = Form(...), alarm_min: int = Form(...), api_rate: int = Form(...), log_rate: int = Form(...)):
    settings.unit, settings.buzzer_mode = unit, buzzer
    settings.api_rate, settings.log_rate = api_rate, log_rate
    await db.save_setting("unit", unit)
    await db.save_setting("buzzer", buzzer)
    await db.save_setting("api_rate", str(api_rate))
    return RedirectResponse(url="/settings", status_code=303)