"""Dedicated UI Designer Tab and Editor."""
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
        .container { max-width: 800px; margin: 30px auto; padding: 0 15px; }
        .card { background: var(--card-bg); border-radius: 8px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
        .card h3 { margin-top: 0; color: var(--primary); border-bottom: 2px solid #eef2f5; padding-bottom: 8px; }
        label { display: block; margin: 12px 0 6px; font-weight: 600; }
        .checkbox-group { display: grid; grid-template-columns: repeat(1, 1fr); gap: 10px; margin-top: 10px; }
        .checkbox-item { background: #f9f9f9; border: 1px solid #ddd; padding: 10px; border-radius: 4px; display: flex; align-items: center; gap: 10px; }
        .btn { background: var(--primary); color: white; border: none; padding: 12px 20px; border-radius: 4px; cursor: pointer; margin-top: 20px; width: 100%; font-weight: bold; font-size: 1rem; }
        .btn:hover { opacity: 0.9; }
    </style>
</head>
<body>
    <header>
        🎨 LCD UI Designer
        <a href="/">← Back to Dashboard</a>
    </header>
    
    <div class="container">
        <div class="card">
            <h3>Configure Active LCD Pages & Widget Order</h3>
            <p style="color: #666; font-size: 0.9rem;">Select and enable the pages you want to cycle through on your hardware LCD display.</p>
            
            <div class="checkbox-group" id="pages-container">
                <label class="checkbox-item"><input type="checkbox" class="page-cb" value="1" checked> <strong>Page 1:</strong> Clock & Date</label>
                <label class="checkbox-item"><input type="checkbox" class="page-cb" value="2" checked> <strong>Page 2:</strong> Indoor Climate & Comfort</label>
                <label class="checkbox-item"><input type="checkbox" class="page-cb" value="3" checked> <strong>Page 3:</strong> Outdoor Climate & UV</label>
                <label class="checkbox-item"><input type="checkbox" class="page-cb" value="4" checked> <strong>Page 4:</strong> Air Quality Index (AQI)</label>
                <label class="checkbox-item"><input type="checkbox" class="page-cb" value="5" checked> <strong>Page 5:</strong> Raspberry Pi System Stats</label>
                <label class="checkbox-item"><input type="checkbox" class="page-cb" value="6" checked> <strong>Page 6:</strong> Moon Phase & Illumination</label>
                <label class="checkbox-item"><input type="checkbox" class="page-cb" value="7" checked> <strong>Page 7:</strong> Station Uptime & Wi-Fi Health</label>
            </div>

            <button class="btn" onclick="saveLayout()">Save UI Layout Configuration</button>
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
            if (res.ok) {
                alert('UI Layout saved successfully!');
            } else {
                alert('Failed to save layout.');
            }
        }

        loadConfig();
    </script>
</body>
</html>
"""

@router.get("/designer", response_class=HTMLResponse)
async def serve_designer():
    return DESIGNER_HTML