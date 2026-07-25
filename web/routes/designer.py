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
        .container { max-width: 1000px; margin: 30px auto; padding: 0 15px; }
        .card { background: var(--card-bg); border-radius: 8px; padding: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px; }
        .card h3 { margin-top: 0; color: var(--primary); border-bottom: 2px solid #eef2f5; padding-bottom: 8px; }
        .widget-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 15px; }
        .widget-box { background: #fff; border: 1px solid #e6eef6; padding: 12px; border-radius: 6px; display: flex; flex-direction: column; gap: 8px; cursor: pointer; transition: all 0.12s; box-shadow: 0 1px 0 rgba(0,0,0,0.02); }
        .widget-box:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(2,136,209,0.08); border-color: #dbeefd; }
        .widget-title { display:flex; gap:10px; align-items:center; }
        .widget-emoji { font-size:1.4rem; }
        .lcd-preview { background:#12220f; color:#36ff6b; font-family:monospace; padding:12px; border-radius:6px; width:280px; }
        .controls { display:flex; gap:10px; margin-top:12px; }
        .btn { background: var(--primary); color: white; border: none; padding: 10px 14px; border-radius: 6px; cursor: pointer; font-weight:600; }
        .btn.secondary { background:#f0ad4e; }
        .btn.danger { background:#d9534f; }
    </style>
</head>
<body>
    <header>
        LCD Screen Designer
        <div>
            <a href="/">Dashboard</a>
            &nbsp;&nbsp;
            <a href="/">UI Designer</a>
        </div>
    </header>

    <div class="container">
        <div class="card">
            <h3>Widget Selection & Active Pages</h3>
            <p style="color: #666; font-size: 0.95rem;">Select a page tab and click any widget below to assign it to your physical 16x2 LCD display.</p>

            <div style="margin:14px 0; display:flex; align-items:center; gap:12px;">
                <label style="font-weight:700;">Select LCD Page:</label>
                <select id="page-select" style="padding:8px 10px; border-radius:6px; min-width:120px;"></select>
                <button id="add-page" class="btn" style="padding:8px 10px;">+ Add Page</button>
            </div>

            <div class="widget-grid" id="widget-tiles">
                <!-- widget tiles inserted here -->
            </div>

            <div style="margin-top:18px;">
                <h4>Live Physical LCD Preview (16x2 Display):</h4>
                <div class="lcd-preview" id="lcd-preview">
                    <div id="preview-line1">Line 1 Loading..</div>
                    <div id="preview-line2">Line 2 Loading..</div>
                </div>
                <div class="controls">
                    <button id="apply-save" class="btn">Apply & Save to LCD</button>
                    <button id="reset-page" class="btn secondary">Reset Page</button>
                    <button id="delete-page" class="btn danger">Delete Page</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const WIDGETS = [
            { id: 1, label: 'Digital Clock', desc: 'Time & Date with Dynamic Hourglass', emoji: '⏳' },
            { id: 2, label: 'Indoor Climate', desc: 'Temp, Humidity & Comfort Level', emoji: '🌡️' },
            { id: 3, label: 'Outdoor Weather', desc: 'Live Weather Forecast & UV', emoji: '🌤️' },
            { id: 4, label: 'Air Quality Index', desc: 'US AQI Score & Particulates', emoji: '🍃' },
            { id: 5, label: 'Pi System Info', desc: 'CPU Temp, Load & RAM', emoji: '🖥️' },
            { id: 6, label: 'Moon Phase', desc: 'Short phase & Illumination', emoji: '🌙' },
            { id: 7, label: 'Diagnostics', desc: 'Uptime & Wi-Fi Status', emoji: '⚡' }
        ];

        let enabledPages = [1,2,3,4,5,6,7];
        let pageWidgetMap = {1:1,2:2,3:3,4:4,5:5,6:6,7:7};
        let selectedPage = 1;
        let previewInterval;

        function makeTile(w) {
            const tile = document.createElement('div');
            tile.className = 'widget-box';
            const title = document.createElement('div');
            title.className = 'widget-title';
            const emoji = document.createElement('div'); emoji.className='widget-emoji'; emoji.innerText = w.emoji;
            const name = document.createElement('div'); name.innerHTML = `<strong>${w.label}</strong>`;
            title.appendChild(emoji); title.appendChild(name);
            const desc = document.createElement('div'); desc.style.color='#666'; desc.style.fontSize='0.9rem'; desc.innerText = w.desc;
            tile.appendChild(title); tile.appendChild(desc);
            const assigned = pageWidgetMap[selectedPage] || selectedPage;
            if (assigned === w.id) { tile.style.border = '2px solid #0288d1'; tile.style.boxShadow = '0 6px 18px rgba(2,136,209,0.08)'; }
            tile.onclick = () => { pageWidgetMap[selectedPage] = w.id; renderTiles(); };
            return tile;
        }

        function renderTiles() {
            const c = document.getElementById('widget-tiles'); c.innerHTML='';
            WIDGETS.forEach(w => c.appendChild(makeTile(w)));
        }

        function populatePageSelect() {
            const sel = document.getElementById('page-select'); sel.innerHTML='';
            enabledPages.forEach(p => { const o=document.createElement('option'); o.value=String(p); o.innerText=`Page ${p}`; if (p===selectedPage) o.selected=true; sel.appendChild(o); });
            sel.onchange = (e) => { selectedPage = parseInt(e.target.value); renderTiles(); restartPreview(); };
        }

        async function loadConfig() {
            const res = await fetch('/api/data'); const data = await res.json();
            enabledPages = data.enabled_pages || enabledPages;
            pageWidgetMap = data.page_widget_map || pageWidgetMap;
            // normalize
            const norm = {}; Object.keys(pageWidgetMap).forEach(k => { norm[parseInt(k)] = parseInt(pageWidgetMap[k]); }); pageWidgetMap = norm;
            if (!enabledPages.includes(selectedPage)) selectedPage = enabledPages[0] || 1;
            populatePageSelect(); renderTiles(); startPreview();
        }

        function startPreview() { stopPreview(); previewInterval = setInterval(async ()=>{ try{ const res=await fetch(`/api/preview?page=${selectedPage}`); const j=await res.json(); document.getElementById('preview-line1').innerText=j.lines[0]; document.getElementById('preview-line2').innerText=j.lines[1]; }catch(e){console.error(e)} }, 1000); }
        function stopPreview(){ if(previewInterval) clearInterval(previewInterval); }
        function restartPreview(){ stopPreview(); startPreview(); }

        document.getElementById('apply-save').onclick = async () => {
            const payload = { enabled_pages: enabledPages, page_widget_map: pageWidgetMap };
            const res = await fetch('/api/settings', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
            if (res.ok) alert('Applied & saved to LCD');
        };
        document.getElementById('reset-page').onclick = () => { pageWidgetMap[selectedPage] = selectedPage; renderTiles(); };
        document.getElementById('delete-page').onclick = () => { if(!confirm('Remove this page from rotation?')) return; enabledPages = enabledPages.filter(p=>p!==selectedPage); delete pageWidgetMap[selectedPage]; selectedPage = enabledPages[0]||1; populatePageSelect(); renderTiles(); restartPreview(); };
        document.getElementById('add-page').onclick = () => { let next=1; while(enabledPages.includes(next)) next++; enabledPages.push(next); pageWidgetMap[next]=next; selectedPage=next; populatePageSelect(); renderTiles(); restartPreview(); };

        loadConfig();
    </script>
</body>
</html>
"""

@router.get("/designer", response_class=HTMLResponse)
async def serve_designer():
    return DESIGNER_HTML