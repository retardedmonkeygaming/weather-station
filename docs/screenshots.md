# Screenshots — what every screen should look like

No images are bundled with the repository; this page describes each screen
so you can verify your install at a glance (and capture your own shots for
a fork or blog post). Suggested capture window: 1280×800 or larger.

---

## 1. Dashboard (`/`)

- **Overall:** near-black navy background (`#020617`), rounded translucent
  "glass" cards with soft borders, Inter font, sky-blue accents.
- **Top bar:** 🌤️ station name, an environment badge reading
  *"all subsystems healthy"* (green) or *"⚠ N subsystem(s) recovering"*
  (amber), nav links Dashboard/Designer/Logs/Settings, and a 🔔 bell with a
  red unread badge.
- **Header row:** date + time on the left; two pills on the right —
  *WiFi: online* (green) and *DHT11: online*.
- **Four metric cards:** big orange indoor temp (trend line beneath), sky
  blue humidity (comfort), emerald outdoor temp (condition text), violet
  AQI (status label).
- **Trend chart:** two smooth lines (orange = indoor, emerald = outdoor)
  over a dark grid; legend labels follow the unit setting
  (`Indoor °C` / `Indoor °F`).
- **LCD mirror:** a green 16×2 panel (or blue, if the designer theme was
  toggled) in monospace with a subtle glow, showing exactly what the
  hardware shows — e.g. `Weather Station` / `v5.2 Booting...` at boot or
  the current widget frame.
- **Secondary row:** animated moon icon + phase name + illumination; UV
  now/max + today's range; System Health list (CPU Temp, CPU Load, RAM,
  Disk, IP, Uptime, WiFi Signal) with a `v<version>` footer.
- **Local-mode variant:** an amber banner appears under the nav and the
  API-driven cards dim to 40% opacity.

## 2. Designer (`/designer`)

- **Page previews:** a row/grid of ten miniature 16×2 green LCDs, one per
  page — active page outlined in sky blue, empty pages greyed. Blue theme
  variant switches the miniatures too.
- **Widget grid:** cards with emoji icon, bold title, grey description,
  and a green **+ QUICK ADD** badge in the corner.
- **Simulator:** the large LCD panel — crisp monospace, 16-char grid,
  custom glyphs drawn as small icons (⏳ ⌛ 🔔 🙂 ☁️ ☀️ ▮ 🌙) with tooltips.
- **Page tabs:** numbered chips 1–10 with the user-assigned names
  (double-click to edit).
- **Action buttons:** Apply & Save (primary), Export JSON, Import JSON,
  Clone page, Rename page.
- **Toasts:** bottom-right stacked confirmations, e.g.
  *"Air Quality added to page 5 — LCD updated"*.

## 3. Setup wizard (`/setup`)

- **First run:** centered card on a soft radial-gradient background, 🛠️
  icon, "First-Time Setup" heading, a 4-dot progress bar, and step panels:
  LCD pin grid (6 inputs) → sensor pins (3 inputs) → Discord fields →
  review `<pre>` block (green monospace summary) with a 💾 Save button.
- **Reconfigure mode (after setup):** identical layout but the heading
  reads "Reconfigure Hardware" and every field is pre-filled with the
  saved values (the bot token field stays empty).
- **After save:** a green "✓ Saved!" line with a *Go to the dashboard →*
  link.

## 4. Settings (`/settings`)

Stacked glass cards: **Hardware Pins** (3×3 grid of pin inputs + "Save
pins" with an inline result line), **Location**, **DHT11 Auto-Calibration**
(raw/offset/calibrated/outdoor values + two action buttons), **Device
Preferences** (two-column selects including the C/F unit, buzzer mode,
screen power, auto-scroll, alarm + time, intervals, Voice/Guest modes,
screen timeout, log compression, Local Storage Only Mode), **Backup &
Restore** ("Run backup now" + result line), and the red-tinted
**Danger Zone** with the factory-reset button.

## 5. Logs (`/logs`)

Header with the total entry count and a row of export buttons (CSV, JSON
bundle, CSV bundle, gzip archive, clear database), then the full-width
history table — timestamp + four value columns, hover row highlight,
em-dashes for missing readings.

## 6. Discord (in your server)

- `/weather` card: moon emoji in the title, condition line, side-by-side
  Indoor/Outdoor fields, Moon field with phase + illumination, Air Quality
  with a status-colored embed stripe, Comfort + LCD page fields, version
  footer, and the condition image (custom or auto-placeholder).
- `/setpage` confirmation: "✅ LCD page updated" with the exact two
  16-character lines shown as code blocks.
- Boot card: 🛰️ "Weather Station Online" with State/Indoor/Outdoor/CPU/RAM
  fields (plus "Recovering" when a subsystem is restarting).

## 7. The LCD itself (1602A)

| Moment | Frame |
|---|---|
| Boot splash | `WEATHER STATION` / ` v5.2 Booting...` then a `▉` progress bar |
| Before setup | `Setup Needed!` / `Visit WebUI!` |
| Web UI visit | `WebUI Connected!` (centered, ~2.5 s) then back to the page |
| Clock page | Centered `\x02 06:15:44` / `16-09-2026` |
| Temp alert | `HIGH TEMP ALERT!` / `In: 32.1C` |
| Alarm | `⏲ ALARM TRIGGER` / `Tap to dismiss...` |
| Settings menu | `1. Temp Unit` / `> Mode: [C]` |
