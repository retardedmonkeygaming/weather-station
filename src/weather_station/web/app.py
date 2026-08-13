import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from weather_station.core.state import state
from weather_station.core.config import settings
from weather_station.persistence.database import DatabaseManager
from weather_station.utils.formatting import calculate_moon_phase
from weather_station.services.system import SystemService

app = FastAPI()
db = DatabaseManager()

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

def format_temp_ui(val):
    if val is None or val == "N/A": return "N/A"
    try:
        v = float(val)
        if settings.unit == "F": return f"{(v * 9/5) + 32:.1f}"
        return f"{v:.1f}"
    except: return "N/A"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, client will receive broadcasts
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def broadcast_updates():
    """Background task to broadcast live updates every 2 seconds"""
    while True:
        try:
            moon = calculate_moon_phase()
            data = {
                "indoor_temp": format_temp_ui(state.indoor_temp),
                "indoor_humid": state.indoor_humid,
                "outdoor_temp": format_temp_ui(state.outdoor_temp),
                "outdoor_humid": state.outdoor_humid,
                "aqi_val": state.aqi_val,
                "aqi_status": state.aqi_status,
                "uv_index": state.uv_index,
                "moon_phase": moon.get('short_name', '--'),
                "lcd_line1": state.last_line1,
                "lcd_line2": state.last_line2,
                "unit": settings.unit,
                "sensor_error": state.sensor_error if hasattr(state, 'sensor_error') else False,
                "timestamp": datetime.now().isoformat()
            }
            await manager.broadcast(data)
        except Exception as e:
            pass
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_updates())

@app.get("/", response_class=HTMLResponse)
async def web_dashboard():
    logs = await db.get_logs(15)
    moon = calculate_moon_phase()
    
    return f"""
<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
    <meta charset="UTF-8">
    <title>SkyCast Weather Station</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🌤️%3C/text%3E%3C/svg%3E">
    <link rel="stylesheet" href="/static/style.css">
    <meta name="theme-color" content="#0288d1">
    <meta name="description" content="Live weather monitoring dashboard">
</head>
<body>
    <nav class="navbar">
        <div class="nav-brand">
            <span class="nav-brand-icon">🌤️</span>
            <span>SkyCast Weather Station</span>
        </div>
        <div class="nav-links">
            <a href="/" class="nav-link active">Dashboard</a>
            <a href="/designer" class="nav-link">UI Designer</a>
            <a href="/logs" class="nav-link">Logs</a>
            <a href="/settings" class="nav-link">Settings</a>
        </div>
        <div class="connection-status">
            <span class="status-dot" id="connection-dot"></span>
            <span id="connection-text">Connecting...</span>
        </div>
    </nav>

    <div class="flex gap-2 mb-3" style="flex-wrap: wrap;">
        <div class="pill"><span class="pill-dot success"></span><span id="sensor-status">Sensors OK</span></div>
        <div class="pill"><span class="pill-dot success"></span><span id="api-status">API Connected</span></div>
        <div class="pill"><span class="pill-dot success"></span><span id="discord-status">Discord Ready</span></div>
    </div>

    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-icon">🏠</div>
            <div class="metric-value" id="indoor-temp">--.-°C</div>
            <div class="metric-label">Indoor Temperature</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">💧</div>
            <div class="metric-value" id="indoor-humid">--%</div>
            <div class="metric-label">Indoor Humidity</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">🌍</div>
            <div class="metric-value" id="outdoor-temp">--.-°C</div>
            <div class="metric-label">Outdoor Temperature</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">🍃</div>
            <div class="metric-value" id="aqi-val">--</div>
            <div class="metric-label">Air Quality Index</div>
            <div class="metric-label" id="aqi-status">--</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">☀️</div>
            <div class="metric-value" id="uv-index">--</div>
            <div class="metric-label">UV Index</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">🌙</div>
            <div class="metric-value" id="moon-phase">{moon.get('short_name', '--')}</div>
            <div class="metric-label">Moon Phase</div>
        </div>
    </div>

    <div class="card">
        <div class="card-header">
            <h3 class="card-title">Physical LCD Display</h3>
            <span class="badge badge-info">Live Mirror</span>
        </div>
        <div class="lcd-preview" id="lcd-preview">Line 1: Loading...\nLine 2: Loading...</div>
    </div>

    <div class="card">
        <div class="card-header">
            <h3 class="card-title">Recent History</h3>
            <span class="text-muted">Last 15 entries</span>
        </div>
        <div class="table-container">
            <table class="table">
                <thead><tr><th>Timestamp</th><th>Indoor Temp</th><th>Indoor Humid</th><th>Outdoor Temp</th><th>Outdoor Humid</th></tr></thead>
                <tbody>
                    {''.join([f"<tr><td>{r[0]}</td><td>{r[1]}°C</td><td>{r[2]}%</td><td>{r[3]}°C</td><td>{r[4]}%</td></tr>" for r in logs])}
                </tbody>
            </table>
        </div>
    </div>

    <footer class="footer">
        <div class="footer-version">
            <span>SkyCast Weather Station v1.0.0</span>
            <span>•</span>
            <span>Last Update: <span id="last-update">--</span></span>
        </div>
        <div class="footer-links">
            <a href="/health">Health Check</a>
            <a href="#" onclick="toggleTheme()">Toggle Theme</a>
        </div>
    </footer>

    <script>
        let ws = null;
        function connectWS() {{
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${{protocol}}//${{window.location.host}}/ws`);
            ws.onopen = () => {{
                document.getElementById('connection-dot').className = 'status-dot';
                document.getElementById('connection-text').textContent = 'Live';
            }};
            ws.onmessage = (e) => {{
                const d = JSON.parse(e.data);
                document.getElementById('indoor-temp').textContent = d.indoor_temp + '°' + d.unit;
                document.getElementById('indoor-humid').textContent = d.indoor_humid + '%';
                document.getElementById('outdoor-temp').textContent = d.outdoor_temp + '°' + d.unit;
                document.getElementById('aqi-val').textContent = d.aqi_val;
                document.getElementById('aqi-status').textContent = d.aqi_status;
                document.getElementById('uv-index').textContent = d.uv_index;
                document.getElementById('moon-phase').textContent = d.moon_phase;
                document.getElementById('lcd-preview').textContent = d.lcd_line1 + '\\n' + d.lcd_line2;
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            }};
            ws.onclose = () => {{
                document.getElementById('connection-dot').className = 'status-dot error';
                document.getElementById('connection-text').textContent = 'Disconnected';
                setTimeout(connectWS, 2000);
            }};
        }}
        function toggleTheme() {{
            const html = document.documentElement;
            const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        }}
        document.addEventListener('DOMContentLoaded', () => {{
            const saved = localStorage.getItem('theme') || 'auto';
            document.documentElement.setAttribute('data-theme', saved);
            connectWS();
        }});
    </script>
</body>
</html>
"""

@app.get("/health")
async def health_check():
    """Health endpoint for observability"""
    stats = SystemService.get_stats()
    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime": stats.get('uptime', 'unknown'),
        "cpu_temp": stats.get('cpu_temp', 'N/A'),
        "cpu_usage": stats.get('cpu_percent', 'N/A'),
        "memory_usage": stats.get('memory_percent', 'N/A'),
        "sensors": "OK" if state.indoor_temp else "ERROR",
        "api_connected": state.outdoor_temp != "N/A",
        "discord_ready": settings.discord_token is not None,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/data")
async def get_live_data():
    moon = calculate_moon_phase()
    return {
        "lcd_line1": state.last_line1,
        "lcd_line2": state.last_line2,
        "indoor_temp": format_temp_ui(state.indoor_temp),
        "indoor_humid": state.indoor_humid,
        "outdoor_temp": format_temp_ui(state.outdoor_temp),
        "aqi_val": state.aqi_val,
        "aqi_status": state.aqi_status,
        "uv_index": state.uv_index,
        "moon_phase": moon.get('short_name', '--'),
        "unit": settings.unit
    }

@app.post("/api/save-page")
async def save_page(request: Request):
    body = await request.json()
    p_id, w_type = int(body.get("page_id", 1)), body.get("widget_type", "")
    state.custom_pages[p_id] = w_type
    await db.save_page_assignment(p_id, w_type)
    return {"status": "success"}

@app.get("/settings", response_class=HTMLResponse)
async def web_settings():
    return f"""
<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
    <meta charset="UTF-8">
    <title>Settings - SkyCast</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav class="navbar">
        <div class="nav-brand"><span class="nav-brand-icon">🌤️</span><span>SkyCast Settings</span></div>
        <div class="nav-links"><a href="/" class="nav-link">Back to Dashboard</a></div>
    </nav>
    
    <div class="card" style="max-width: 600px;">
        <h2>Device Preferences</h2>
        <form action="/update-settings" method="post">
            <div class="form-group">
                <label class="form-label">Temperature Unit</label>
                <select name="unit" class="form-control">
                    <option value="C" {"selected" if settings.unit=="C" else ""}>Celsius</option>
                    <option value="F" {"selected" if settings.unit=="F" else ""}>Fahrenheit</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Buzzer Mode</label>
                <select name="buzzer" class="form-control">
                    <option value="ALL" {"selected" if settings.buzzer_mode=="ALL" else ""}>All Sounds</option>
                    <option value="MUTE" {"selected" if settings.buzzer_mode=="MUTE" else ""}>Mute</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">API Rate (minutes)</label>
                <input type="number" name="api_rate" class="form-control" value="{settings.api_rate}">
            </div>
            <button type="submit" class="btn btn-primary">Save Settings</button>
        </form>
    </div>
</body>
</html>
"""

@app.post("/update-settings")
async def update_settings(unit: str = Form(...), buzzer: str = Form(...), api_rate: int = Form(...)):
    settings.unit, settings.buzzer_mode, settings.api_rate = unit, buzzer, api_rate
    await db.save_setting("unit", unit)
    await db.save_setting("buzzer", buzzer)
    await db.save_setting("api_rate", str(api_rate))
    return RedirectResponse(url="/settings", status_code=303)

@app.get("/designer", response_class=HTMLResponse)
async def ui_designer():
    # Simplified designer - full implementation would be similar to dashboard
    return f"""
<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
    <meta charset="UTF-8">
    <title>UI Designer - SkyCast</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav class="navbar">
        <div class="nav-brand"><span class="nav-brand-icon">🎨</span><span>LCD Designer</span></div>
        <div class="nav-links"><a href="/" class="nav-link">Back to Dashboard</a></div>
    </nav>
    <div class="card">
        <h2>LCD Screen Designer</h2>
        <p>Select widgets for each LCD page. Changes apply immediately.</p>
        <div id="page-tabs" style="display:flex; gap:8px; margin: 20px 0;"></div>
        <div class="lcd-preview" id="lcd-preview">Loading preview...</div>
    </div>
    <script>
        setInterval(async () => {{
            const res = await fetch('/api/data');
            const d = await res.json();
            document.getElementById('lcd-preview').textContent = d.lcd_line1 + '\\n' + d.lcd_line2;
        }}, 1000);
    </script>
</body>
</html>
"""

@app.get("/logs", response_class=HTMLResponse)
async def view_logs():
    logs = await db.get_logs(100)
    total = await db.get_total_logs()
    rows = "".join([f"<tr><td>#{i+1}</td><td>{r[0]}</td><td>{r[1]}°C</td><td>{r[2]}%</td><td>{r[3]}°C</td><td>{r[4]}%</td></tr>" for i, r in enumerate(logs)])
    return f"""
<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head><meta charset="UTF-8"><title>Logs - SkyCast</title><link rel="stylesheet" href="/static/style.css"></head>
<body>
    <nav class="navbar"><div class="nav-brand">📊 Logs</div><div class="nav-links"><a href="/" class="nav-link">Dashboard</a></div></nav>
    <div class="card"><p>Total Entries: <strong>{total}</strong></p></div>
    <div class="card"><div class="table-container"><table class="table"><thead><tr><th>ID</th><th>Timestamp</th><th>Indoor T</th><th>Indoor H</th><th>Outdoor T</th><th>Outdoor H</th></tr></thead><tbody>{rows}</tbody></table></div></div>
</body>
</html>
"""
