"""Responsive Web Dashboard featuring Live LCD, Interactive Charts, Settings, and UI Designer."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raspberry Pi Weather Station</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary: #0288d1;
            --bg: #f4f6f9;
            --card-bg: #ffffff;
            --text: #333333;
            --lcd-bg: #2b3a2a;
            --lcd-text: #00ff66;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; }
        header { background: var(--primary); color: white; padding: 15px 20px; text-align: center; font-size: 1.4rem; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .container { max-width: 1100px; margin: 20px auto; padding: 0 15px; display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
        .card { background: var(--card-bg); border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
        .card h3 { margin-top: 0; color: var(--primary); border-bottom: 2px solid #eef2f5; padding-bottom: 8px; }
        
        /* Simulated 16x2 Green LCD */
        .lcd-container { background: var(--lcd-bg); color: var(--lcd-text); font-family: "Courier New", Courier, monospace; font-size: 1.3rem; font-weight: bold; padding: 15px; border-radius: 8px; border: 4px solid #1a2419; box-shadow: inset 0 0 10px rgba(0,0,0,0.8); letter-spacing: 2px; line-height: 1.5; }
        .lcd-line { white-space: pre; }

        /* Form & Settings Controls */
        label { display: block; margin: 10px 0 4px; font-weight: 600; font-size: 0.85rem; }
        select, input[type="number"], input[type="text"] { width: 100%; padding: 8px 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        .checkbox-group { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 6px; }
        .btn { background: var(--primary); color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; margin-top: 15px; width: 100%; font-weight: bold; }
        .btn:hover { opacity: 0.9; }
        .btn-danger { background: #d32f2f; margin-top: 8px; }
    </style>
</head>
<body>
    <header>🌦️ Raspberry Pi Weather Station</header>
    
    <div class="container">
        <div class="card">
            <h3>📟 Live LCD Display</h3>
            <div class="lcd-container">
                <div id="lcd-line1" class="lcd-line">Initializing...</div>
                <div id="lcd-line2" class="lcd-line">Please wait</div>
            </div>
            <p style="font-size:0.85rem; color:#666; margin-top:10px;">Active Page: <span id="current-page-num">1</span>/7</p>
        </div>

        <div class="card">
            <h3>📊 Current Metrics</h3>
            <p><strong>Indoor Temp:</strong> <span id="val-in-temp">--</span></p>
            <p><strong>Indoor Humidity:</strong> <span id="val-in-hum">--</span></p>
            <p><strong>Outdoor Temp:</strong> <span id="val-out-temp">--</span></p>
            <p><strong>Outdoor Humidity:</strong> <span id="val-out-hum">--</span></p>
            <p><strong>Air Quality Index:</strong> <span id="val-aqi">--</span></p>
        </div>

        <div class="card">
            <h3>🎨 LCD UI Designer</h3>
            <label>Enable / Disable LCD Pages</label>
            <div class="checkbox-group">
                <label><input type="checkbox" class="page-cb" value="1" checked> 1: Clock</label>
                <label><input type="checkbox" class="page-cb" value="2" checked> 2: Indoor</label>
                <label><input type="checkbox" class="page-cb" value="3" checked> 3: Outdoor</label>
                <label><input type="checkbox" class="page-cb" value="4" checked> 4: AQI</label>
                <label><input type="checkbox" class="page-cb" value="5" checked> 5: Pi System</label>
                <label><input type="checkbox" class="page-cb" value="6" checked> 6: Moon Phase</label>
                <label><input type="checkbox" class="page-cb" value="7" checked> 7: Uptime</label>
            </div>
            <button class="btn" onclick="saveUIConfig()">Save Layout Design</button>
        </div>

        <div class="card">
            <h3>⚙️ Settings & Alerts</h3>
            <label for="set-unit">Temperature Unit</label>
            <select id="set-unit">
                <option value="C">Celsius (°C)</option>
                <option value="F">Fahrenheit (°F)</option>
            </select>

            <label for="set-buzzer">Buzzer Mode</label>
            <select id="set-buzzer">
                <option value="ALL">All Beeps Enabled</option>
                <option value="ERR">Errors Only</option>
                <option value="MUTE">Mute All Audio</option>
            </select>

            <label for="set-high-alert">High Temp Alert Threshold (°C)</label>
            <input type="number" id="set-high-alert" step="0.5">

            <label for="set-low-alert">Low Temp Alert Threshold (°C)</label>
            <input type="number" id="set-low-alert" step="0.5">

            <label for="set-webhook">Webhook URL (Discord/Telegram)</label>
            <input type="text" id="set-webhook" placeholder="https://discord.com/api/webhooks/...">

            <button class="btn" onclick="saveWebSettings()">Save Configuration</button>
            <button class="btn btn-danger" onclick="factoryReset()">Factory Reset</button>
        </div>

        <div class="card" style="grid-column: 1 / -1;">
            <h3>📈 Historical Temperature Log (24h)</h3>
            <canvas id="tempChart" height="100"></canvas>
        </div>
    </div>

    <script>
        let chart;

        async function fetchState() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                
                if (data.last_lcd_rendered_text && data.last_lcd_rendered_text.length >= 2) {
                    document.getElementById('lcd-line1').innerText = data.last_lcd_rendered_text[0];
                    document.getElementById('lcd-line2').innerText = data.last_lcd_rendered_text[1];
                }
                document.getElementById('current-page-num').innerText = data.current_page;

                document.getElementById('val-in-temp').innerText = data.indoor_temp ? `${data.indoor_temp.toFixed(1)}${data.temp_unit}` : 'N/A';
                document.getElementById('val-in-hum').innerText = data.indoor_humid ? `${data.indoor_humid.toFixed(0)}%` : 'N/A';
                document.getElementById('val-out-temp').innerText = data.outdoor_temp ? `${data.outdoor_temp.toFixed(1)}${data.temp_unit}` : 'N/A';
                document.getElementById('val-out-hum').innerText = data.outdoor_humid ? `${data.outdoor_humid.toFixed(0)}%` : 'N/A';
                document.getElementById('val-aqi').innerText = `${data.aqi_val} (${data.aqi_status})`;
            } catch (e) { console.error('Error fetching data', e); }
        }

        async function loadSettingsUI() {
            const res = await fetch('/api/data');
            const data = await res.json();
            document.getElementById('set-unit').value = data.temp_unit;
            document.getElementById('set-buzzer').value = data.buzzer_mode;
            document.getElementById('set-high-alert').value = data.high_temp_threshold || 35.0;
            document.getElementById('set-low-alert').value = data.low_temp_threshold || 5.0;
            document.getElementById('set-webhook').value = data.webhook_url || '';
            
            const activePages = data.enabled_pages || [1,2,3,4,5,6,7];
            document.querySelectorAll('.page-cb').forEach(cb => {
                cb.checked = activePages.includes(parseInt(cb.value));
            });
        }

        async function saveWebSettings() {
            const payload = {
                temp_unit: document.getElementById('set-unit').value,
                buzzer_mode: document.getElementById('set-buzzer').value,
                high_temp_threshold: parseFloat(document.getElementById('set-high-alert').value),
                low_temp_threshold: parseFloat(document.getElementById('set-low-alert').value),
                webhook_url: document.getElementById('set-webhook').value
            };
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            alert('Settings and alerts saved successfully!');
        }

        async function saveUIConfig() {
            const enabledPages = Array.from(document.querySelectorAll('.page-cb:checked')).map(cb => parseInt(cb.value));
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled_pages: enabledPages })
            });
            alert('LCD layout designer configuration saved!');
        }

        async function factoryReset() {
            if (confirm('Are you sure you want to reset all settings?')) {
                await fetch('/api/reset', { method: 'POST' });
                location.reload();
            }
        }

        async function initChart() {
            const res = await fetch('/api/history');
            const logs = await res.json();
            const labels = logs.map(l => l.timestamp.split(' ')[1] || l.timestamp);
            const inTemps = logs.map(l => l.indoor_temp);
            const outTemps = logs.map(l => l.outdoor_temp);

            const ctx = document.getElementById('tempChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        { label: 'Indoor Temp', data: inTemps, borderColor: '#0288d1', fill: false },
                        { label: 'Outdoor Temp', data: outTemps, borderColor: '#e65100', fill: false }
                    ]
                }
            });
        }

        setInterval(fetchState, 1000);
        loadSettingsUI();
        initChart();
    </script>
</body>
</html>
"""

@router.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return HTML_CONTENT