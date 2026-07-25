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
            
            <div id="widget-selection">
                <!-- Per-page mapping: page slot, enable checkbox, widget selector -->
                <div style="display:grid; gap:10px;"> 
                    <!-- rows populated by JS -->
                </div>
            </div>

            <div style="margin-top:16px;">
                <h4 style="margin-bottom:8px;">Preview</h4>
                <div class="lcd-preview" style="background:#222; color:#0f0; font-family:monospace; padding:12px; border-radius:6px;">
                    <div id="preview-line1">--</div>
                    <div id="preview-line2">--</div>
                </div>
            </div>

            <button class="btn" onclick="saveLayout()">Save Widget Configuration</button>
        </div>
    </div>

    <script>
        const WIDGETS = [
            { id: 1, label: 'Clock & Date' },
            { id: 2, label: 'Indoor Comfort' },
            { id: 3, label: 'Outdoor & UV' },
            { id: 4, label: 'AQI & Particulates' },
            { id: 5, label: 'Pi Stats' },
            { id: 6, label: 'Moon Phase' },
            { id: 7, label: 'Uptime & Wi-Fi' }
        ];

        function makeRow(page, enabled, assignedWidget) {
            const wrapper = document.createElement('label');
            wrapper.className = 'widget-box';
            wrapper.style.display = 'flex';
            wrapper.style.justifyContent = 'space-between';
            wrapper.style.alignItems = 'center';

            const left = document.createElement('div');
            left.style.display = 'flex';
            left.style.alignItems = 'center';
            left.style.gap = '10px';

            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'page-cb';
            cb.value = String(page);
            cb.checked = enabled;

            const title = document.createElement('span');
            title.innerText = `Page ${page}`;

            left.appendChild(cb);
            left.appendChild(title);

            const right = document.createElement('div');
            right.style.display = 'flex';
            right.style.gap = '8px';
            right.style.alignItems = 'center';

            const sel = document.createElement('select');
            sel.className = 'widget-sel';
            sel.dataset.page = String(page);
            WIDGETS.forEach(w => {
                const o = document.createElement('option');
                o.value = String(w.id);
                o.innerText = w.label;
                if (w.id === assignedWidget) o.selected = true;
                sel.appendChild(o);
            });

            const previewBtn = document.createElement('button');
            previewBtn.className = 'btn';
            previewBtn.style.width = 'auto';
            previewBtn.style.padding = '6px 10px';
            previewBtn.innerText = 'Preview';
            previewBtn.onclick = async (e) => {
                e.preventDefault();
                const wid = sel.value;
                const res = await fetch(`/api/preview?widget=${encodeURIComponent(wid)}`);
                const j = await res.json();
                document.getElementById('preview-line1').innerText = j.lines[0];
                document.getElementById('preview-line2').innerText = j.lines[1];
            };

            right.appendChild(sel);
            right.appendChild(previewBtn);

            wrapper.appendChild(left);
            wrapper.appendChild(right);
            return wrapper;
        }

        async function loadConfig() {
            const res = await fetch('/api/data');
            const data = await res.json();
            const activePages = new Set(data.enabled_pages || [1,2,3,4,5,6,7]);
            const map = data.page_widget_map || {1:1,2:2,3:3,4:4,5:5,6:6,7:7};

            const container = document.querySelector('#widget-selection > div');
            container.innerHTML = '';
            for (let p=1; p<=7; p++) {
                const enabled = activePages.has(p);
                const assigned = map[String(p)] || map[p] || p;
                container.appendChild(makeRow(p, enabled, assigned));
            }
        }

        async function saveLayout() {
            const enabledPages = Array.from(document.querySelectorAll('.page-cb:checked')).map(cb => parseInt(cb.value));
            const pageWidgetMap = {};
            document.querySelectorAll('.widget-sel').forEach(sel => {
                pageWidgetMap[sel.dataset.page] = parseInt(sel.value);
            });

            const payload = { enabled_pages: enabledPages, page_widget_map: pageWidgetMap };
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
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