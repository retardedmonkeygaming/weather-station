# Dashboard Guide — the web UI at `/`

A dark glassmorphism dashboard. Sign in with `WEB_AUTH_USERNAME` /
`WEB_AUTH_PASSWORD` (default `admin` / `admin`; `/api/health` is always open
for probes).

---

## Layout tour

> Screenshot reference: see [screenshots.md](screenshots.md#1-dashboard).

1. **Top bar** — station name, environment badge
   ("all subsystems healthy" / "⚠ N subsystem(s) recovering"), nav links,
   and the notification bell.
2. **Local-mode banner** (only when Local Storage Only Mode is ON) — an
   amber strip explaining that Open-Meteo is disabled and which fields are
   frozen.
3. **Header row** — live clock line and two status pills: WiFi online/offline
   and DHT11 online/error.
4. **Metric cards** — Indoor Temp (with trend), Indoor Humidity (with
   comfort level), Outdoor Temp (with condition text), Air Quality
   (US AQI with status label). In local mode the API-driven cards dim to
   40% opacity.
5. **Trend chart** — Chart.js line chart, indoor vs outdoor temperature
   from SQLite history. The legend and table headers follow your C/F
   unit setting. Refreshes every 30 s (HTMX) plus a slow fallback poll.
6. **LCD Mirror** — a pixel-faithful green 16×2 panel rendering exactly
   what the physical LCD shows (custom glyphs included). It fades to 45%
   opacity while Guest Mode is dimming the hardware.
7. **Secondary cards** — moon phase (animated icon per phase), UV now/max
   with today's min/max range, and the System Health card (CPU temp, CPU
   load, RAM, disk, IP, uptime, WiFi signal) refreshed every 10 s.
8. **Recent History table** — the latest rows from `weather_logs`.

## The notification bell

Click the 🔔 to open the panel. Kinds: 🌡️ temperature alert, ⏰ alarm,
⚠️ error (subsystem crash, DHT offline, WiFi down), ℹ️ info (backup done,
MQTT test, pins changed). The red badge counts unread items; "Clear all"
empties it. Polled every 15 s.

## Settings page (`/settings`)

Grouped cards, top to bottom:

| Card | What it does |
|---|---|
| **Hardware Pins** | Re-configure every GPIO pin after setup (validates 0–27 + uniqueness; applies on restart) |
| **Location** | Latitude/longitude for Open-Meteo |
| **DHT11 Auto-Calibration** | Shows raw temp, current offset, calibrated value; auto-calibrates against the outdoor API or resets to 0.0 |
| **Device Preferences** | Unit (C/F), buzzer mode, screen power, auto-scroll, daily alarm + time, API/log intervals, Voice Mode, Guest Mode, screen timeout, log compression, Local Storage Only Mode |
| **Backup & Restore** | "Run backup now" — writes `backups/backup_YYYY-MM-DD/` immediately (auto-backup runs every 24 h) |
| **Danger Zone** | Factory reset — restores defaults and clears custom page assignments |

## Logs page (`/logs`)

Full history table (latest 100 shown, total count in the header) with:

- 📥 Export CSV — the whole `weather_logs` table
- 🗄️ Export All (JSON) — logs + settings + pages + names in one bundle
- 🗂️ Export All (CSV) — same bundle, logs as CSV
- 🗜️ Archive old logs — gzip rows older than 30 days out of the live table
- 🗑️ Clear database — wipe all history (confirm required)

## Live data contract

The dashboard polls `GET /api/data` every 5 s. The LCD mirror renders
`lcd_line1` / `lcd_line2` — the exact fitted 16-char rows the physical
panel received, so the web view never drifts from the hardware.
