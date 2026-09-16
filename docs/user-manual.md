# User Manual — Raspberry Pi Weather Station

Everything you need to install, configure, and live with your weather
station. Version-specific changes live in [`CHANGELOG.md`](../CHANGELOG.md).

---

## 1. What you need

- Raspberry Pi (any model with 40-pin GPIO; Pi 3/4/5 recommended) running
  Raspberry Pi OS — or any desktop machine for development (mock hardware)
- 1602A / HD44780 16×2 character LCD
- DHT11 temperature/humidity sensor (10k pull-up on the data line recommended)
- Tactile push button and an active buzzer
- Jumper wires; optional 220Ω resistor for the LCD backlight

For desktop development none of the hardware is required — the station runs
in mock mode with an on-screen `[SIMULATED]` LCD.

---

## 2. Installation

```bash
sudo apt update && sudo apt install -y python3-venv espeak
git clone <your-repo> weather-station && cd weather-station
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`espeak` is optional (Voice Mode); everything else comes from `requirements.txt`.

### Docker alternative

```bash
docker compose up -d        # → http://localhost:8000, mock hardware, ./data/ persists SQLite
```

---

## 3. First run — the setup wizard

Start the station:

```bash
python main.py
```

What you will see:

1. On the **LCD**: a boot splash (`WEATHER STATION`, a loading bar, sensor
   and network probes). If the DHT11 is not connected yet, the panel shows
   one non-blocking notice and — **before setup has ever been completed** —
   stands on `Setup Needed! / Visit WebUI!` instead of locking up.
2. In the **browser**: `http://<pi-ip>:8000/` redirects to `/setup` (sign in
   `admin` / `admin`).

The wizard has four steps:

| Step | You enter | Notes |
|---|---|---|
| 1. LCD Pins | RS, EN, D4–D7 | BCM numbering; every pin must be unique |
| 2. Sensors | DHT11 data, button, buzzer pins | Same uniqueness rule |
| 3. Discord (optional) | Bot token, live-update channel, admin role, reminder channel, weather image URL | See the [Discord Guide](discord-guide.md) |
| 4. Review & Save | — | Writes `.env`, mirrors pins into `config.py`, creates any missing folders |

After saving: **restart the station** (`Ctrl+C`, then `python main.py`) so
the new pins take effect, and click **Go to the dashboard**.

**Idempotent by design:** the wizard never duplicates config. Re-running it
(visit `/setup` any time, or delete `.env` to simulate a fresh start)
updates the same `.env` keys in place and pre-fills everything you already
saved — pins, channels, role, image URL. Your bot token is never displayed;
leave it blank to keep the saved one.

---

## 4. Changing pins later

Settings → **Hardware Pins**. Same validation as the wizard (BCM 0–27,
unique). Saving writes the same `.env` keys and tells you which pins
changed; a restart applies them.

---

## 5. Daily use

### Physical button

| Gesture | Action |
|---|---|
| Tap | Next LCD page (Voice Mode: also speaks the conditions) |
| Triple-tap | Physical settings menu — tap to advance, **hold ~1.5 s** to change the highlighted item |
| Hold 5 s | Reboot (release to confirm) |
| Hold 10 s | Shutdown (release to confirm) |
| Any tap | Dismisses a ringing alarm or a temperature alert; wakes a blanked screen |

The settings menu cycles: unit (C/F) · buzzer (ALL/ERR/MUTE) · screen
power · auto-scroll · alarm on/off · alarm hour/minute · API interval ·
log interval · factory reset (hold 3 s on item 10).

### Web UI

- `/` **Dashboard** — live metrics, indoor-vs-outdoor chart (refreshes every
  30 s), the 16×2 LCD mirror (what the panel shows, byte for byte), moon
  phase, UV & forecast, system health, and the notification bell.
- `/designer` **Designer** — assign widgets to LCD pages 1–10. See the
  [Designer Guide](designer-guide.md).
- `/logs` **Logs** — full history table, CSV/JSON exports, gzip archiving,
  clear-database.
- `/settings` **Settings** — pins, location, DHT11 calibration, all
  preferences, backups, factory reset.

### Notification bell

Temp alerts, alarm triggers, subsystem crashes/restarts, backups, and
MQTT test publishes all land in the bell (newest first, 50-entry cap).
Clear them with "Clear all".

---

## 6. Features in depth

### LCD design system (strict 16×2)
Every string is engineered for 16 columns and the driver hard-clips/pads as
a final guard — the HD44780 never wraps into unseen DDRAM. Eight custom
glyphs (`\x00`–`\x07`: hourglass ×2, bell, smile, cloud, sun, block, moon)
are burned **once** at startup and never rewritten at runtime, so no render
cycle is ever interrupted by a CGRAM bank switch.

### Clock page
Time and date are centered on the panel (alarm bell glyph shown when the
alarm is armed).

### Screen power & timeout
- **Screen OFF** (settings) powers the panel down; a tap brings it back to ON.
- **Screen timeout** blanks the panel after N idle seconds (30 s default,
  0 = never blank); a tap **or a web-UI visit** wakes it.

### Guest Mode
After 30 minutes without a button press the LCD dims (contrast PWM when
wired, backlight otherwise) and the buzzer goes silent — data keeps
rendering. Any press restores everything. Toggle in Settings.

### Voice Mode
Speaks the indoor/outdoor temps + humidity on tap, announces ≥2 °C indoor
shifts, and reads temperature alerts aloud. Uses `espeak` (preferred) or
`pyttsx3`. Toggle in Settings.

### Local Storage Only Mode
Settings toggle that makes **zero** Open-Meteo calls: outdoor weather, UV,
and AQI freeze at their last known values, the dashboard shows a warning
banner, and only DHT11 + SQLite data stays live. Good for offline/air-gapped
installations.

### Auto-Backup
Every 24 hours the station writes a full backup into
`backups/backup_YYYY-MM-DD/`: a consistent SQLite copy (`VACUUM INTO`) plus
a human-readable `snapshot.json` (logs + settings + pages). Trigger one
any time from Settings → "Run backup now".

### Dynamic display
Opening the web UI flashes `WebUI Connected!` on the physical LCD once and
counts as user activity. Before setup, the panel stands on
`Visit WebUI!` so you always know where to fix things.

### Alerts & alarm
High/low temperature alerts (thresholds configurable via Discord
`/set-alert` or the settings DB) take over the LCD with an alert frame,
beep, bell notification, and (optionally) a spoken warning. The daily alarm
rings the buzzer (quiet hours 23:00–07:00 respected) and shows an
alarm frame until dismissed. Discord also posts reminders — see the
[Discord Guide](discord-guide.md).

### Data & exports
- History charts + tables (dashboard & logs pages)
- `GET /api/export/all?format=json|csv` — full DB bundle
- `POST /api/archive-logs` — gzip rows older than 30 days
- Auto-Backup (above)

---

## 7. Maintenance

- **Logs**: `weather_station.log` rotates at 5 MB × 5 files.
  `LOG_LEVEL=DEBUG` for verbose console output.
- **Updates**: `git pull && pip install -r requirements.txt`; settings and
  pages live in SQLite and survive updates. Run a manual backup first.
- **Factory reset**: Settings → Danger Zone, or hold item 10 in the physical
  menu for 3 s. Wipes settings + custom pages (log history is kept).

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| LCD blank at boot | Check wizard pins vs wiring; adjust the 1602A contrast trim pot |
| `Sensor Missing` / DHT errors | Verify the data pin + 10k pull-up; the station keeps probing and self-heals on reconnect |
| LCD shows `Visit WebUI!` | Setup not completed yet — finish the wizard at `http://<pi-ip>:8000/` |
| Wrong temperature | Settings → DHT11 auto-calibration (offsets against the outdoor API) |
| Locked out of the web UI | `.env`: set `WEB_AUTH_ENABLED=OFF` (or new credentials), restart |
| Designer page empty | The widget assignment was cleared — re-assign in `/designer`, or check the defaults (pages 1–6) |
| Discord bot silent | Token saved? Bot invited with `bot` + `applications.commands` scopes? See the [Discord Guide](discord-guide.md) |
| MQTT test fails (502) | Broker unreachable from the Pi — check host/port/credentials |

More release context: [`CHANGELOG.md`](../CHANGELOG.md).
