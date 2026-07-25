"""Dedicated UI Designer Tab with Widget Selection & Layout Controls."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["designer"])

DESIGNER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weather Station - UI Designer</title>
    <style>
        :root {
            --primary: #0288d1;
            --bg: #f4f6f9;
            --card-bg: #ffffff;
            --text: #333333;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; }
        header { background: var(--primary); color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; font-size: 1.4rem; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        header a { color: white; text-decoration: none; font-size: 0.9rem; background: rgba(255,255,255,0.2); padding: 8px 12px; border-radius: 4px; }
        .container { max-width: 900px; margin: 30px auto; padding: 0 15px; }
        .card { background: var(--card-bg); border-radius: 8px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px; }
        .card h3 { margin-top: 0; color: var(--primary); border-bottom: 2px solid #eef2f5; padding-bottom: 8px; }
        .widget-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px; margin-top: 15px; }
        .widget-box { background: #f8fafc; border: 2px solid #e2e8f0; padding: 12px; border-radius: 6px; display: flex; align-items: center; gap: 10px; cursor: pointer; transition: all 0.2s; }
        .widget-box:hover { border-color: var(--primary); }
        .widget-box input { transform: scale(1.2); }
        .btn { background: var(--primary); color: white; border: none; padding: 12px 20px; border-radius: 4px; cursor: pointer; margin-top: 20px; width: 100%; font-weight: bold; font-size: 1rem; }
        .btn:hover { opacity: 0.9; }
    </style>
</head>
<body>
    <header>
        🎨 LCD UI Designer & Widget Selector
        <a href="/">← Back to Dashboard</a>
    </header>
    
    <div class="container">
        <div class="card">
            <h3>Widget Selection & Active Pages</h3>
            <p style="color: #666; font-size: 0.9rem;">Enable or disable individual display pages and widgets for hardware auto-scrolling:</p>
            
            <div class="widget-grid" id="widget-selection">
                <label class="widget-box"><input type="checkbox" class="page-cb" value="1" checked> 📅 Clock & Date Widget</label>
                <label class="widget-box"><input type="checkbox" class="page-cb" value="2" checked> 🏠 Indoor Comfort Widget</label>
                <label class="widget-box"><input type="checkbox" class="page-cb" value="3" checked> 🌤️ Outdoor & UV Widget</label>
                <label class="widget-box"><input type="checkbox" class="page-cb" value="4" checked> 🍃 AQI & Particulate Widget</label>
                <label class="widget-box"><input type="checkbox" class="page-cb" value="5" checked> 🖥️ Pi Stats Widget</label>
                <label class="widget-box"><input type="checkbox" class="page-cb" value="6" checked> 🌙 Moon Phase Widget</label>
                <label class="widget-box"><input type="checkbox" class="page-cb" value="7" checked> 📶 Uptime & Wi-Fi Widget</label>
            </div>

            <button class="btn" onclick="saveLayout()">Save Widget Configuration</button>
        </div>
    </div>

    <script>
        async function loadConfig() {
            const res = await fetch('/api/data');
            const data = await res.json();
            const activePages = data.enabled_pages || [1,2,3,4,5,6,7];
            document.querySelectorAll('.page-cb').forEach(cb => {
                cb.checked = activePages.includes(parseInt(cb.value));
            });
        }

        async function saveLayout() {
            const enabledPages = Array.from(document.querySelectorAll('.page-cb:checked')).map(cb => parseInt(cb.value));
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled_pages: enabledPages })
            });
            if (res.ok) alert('UI Widget layout saved successfully!');
        }

        loadConfig();
    </script>
</body>
</html>
"""

@router.get("/designer", response_class=HTMLResponse)
async def serve_designer():
    return DESIGNER_HTML