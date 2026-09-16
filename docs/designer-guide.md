# Designer Guide — building your LCD pages

The designer at `/designer` maps widgets onto the ten LCD pages and shows
exactly what the 1602A will render.

---

## Layout tour

> Screenshot reference: see [screenshots.md](screenshots.md#2-designer).

1. **Top bar** — theme toggle (green/blue), active page indicator.
2. **Page previews** — a tiny live 16×2 thumbnail for every page 1–10,
   rendered by the same server-side engine as the hardware. Grey = empty,
   sky ring = active page, click = open that page.
3. **Widget grid** — cards for every widget with icon, title, description,
   and a green **+ Quick add** badge.
4. **LCD simulator** — the large pixel-perfect panel (monospace, exact
   16-char grid) showing the selected widget for the active page, custom
   glyphs rendered as icons.
5. **Page tabs 1–10** — double-click (or "Rename page") to rename;
   "Clone page" copies the current page's widget + name to any target page.
6. **Actions** — Apply & Save, Export JSON, Import JSON.

## Widget catalog

| Widget | Icon | Shows |
|---|---|---|
| Digital Clock | 🕒 | Centered time + date, alarm bell when armed |
| Indoor Climate | 🌡️ | Indoor temp (with trend arrow) + humidity; comfort level |
| Outdoor Weather | ☀️ | Outdoor temp + humidity, forecast condition; `*`/`!` flags when offline |
| Weather Forecast | 📅 | Daily min/max + UV now/peak (cached values in Local Mode) |
| Air Quality | 🍃 | US AQI score + status label, PM2.5/PM10 |
| Air Pollutants | 🌫️ | PM2.5 and PM10 details |
| Moon Phase | 🌙 | Phase glyph + name, illumination % |
| Humidity Gauge | 💧 | Indoor humidity detail |
| UV Index | 🔆 | Current + peak UV |
| Comfort Level | 😊 | Indoor comfort classification |
| Diagnostics | ⚡ | DHT + WiFi status |
| Pi System | 🤖 | CPU temp/load, RAM usage |

Plus **custom layout JSON blocks** — any
`{"type":"custom","lines":["16 chars or less","16 chars or less"]}`
payload saved onto a page.

## Core actions

| Action | What happens |
|---|---|
| Click a widget card | Loads its frame into the simulator (preview only) |
| **+ Quick add** | Select + save to the active page + jump the physical LCD there + toast |
| **Apply & Save** | Persists the page assignment and immediately switches the physical LCD to it |
| **Clone page** | Copies widget + tab name to a chosen target page |
| **Rename page** | Inline tab editor (persisted in `page_meta`) |
| **Export JSON** | Downloads `lcd_layout_<date>.json` with all pages + names (also copies to clipboard) |
| **Import JSON** | Validates and applies a layout; reports per-page errors for skipped entries |

## The 16×2 contract

Every widget frame is engineered for exactly 16 columns × 2 rows. The
server renders the same frame the display loop will send, and the driver
hard-clips/pads as a final guard — so the simulator, the thumbnails, and
the physical panel can never disagree.
