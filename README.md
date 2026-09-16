# Raspberry Pi Weather Station

A modular, production-grade weather station for the Raspberry Pi: 1602A LCD
with a strict 16×2 design system, DHT11 sensor, buzzer & tap button, and a
Tailwind dark-glass web dashboard with a page designer, Discord bot, MQTT
publishing, voice mode, and a supervised async core that self-heals from
sensor and network failures.

## Features

- **16×2 LCD design system** — every row hard-clipped/padded to exactly
  16 chars (no HD44780 wrap-around), burn-once custom glyphs (⏳ ⌛ 🔔 🙂 ☁ ☀ ▮ 🌙)
- **Web dashboard** — glassmorphism dark UI, Chart.js indoor-vs-outdoor
  trends (HTMX auto-refresh), live LCD mirror, system health card, and a
  notification center (bell icon)
- **LCD Page Designer** — `/designer`: page tabs 1–10, widget grid with
  Quick Add, drag-and-drop, page thumbnails, clone/rename, JSON
  import/export, pixel-perfect green/blue LCD simulator
- **Discord bot** — `/weather` `/forecast` `/setpage` `/alarm-on|off`
  `/set-alert` `/status-embed` `/liveupdate`, rich weather-card embeds with
  moon emoji, role-gated admin commands, TTS "speak the weather"
- **MQTT publishing** — JSON snapshots to any broker on a cadence
- **Voice Mode** — espeak/pyttsx3 speaks temps on tap and big changes
- **Guest Mode** — 30-min idle dims the LCD (optional contrast PWM) and
  silences the buzzer
- **Screen Timeout** — LCD blanks after N seconds idle, wakes on tap
- **Supervised tasks** — every background loop restarts after a crash with
  a cool-down; failures surface in `/api/health` and the bell icon
- **Edge-case hardening** — DHT11 unplugged mid-run and permanent WiFi
  loss are handled with fast retries, stale-but-labeled data, and
  self-healing recovery
- **Data export** — CSV/JSON full-history export, gzip log archiving
- **Basic auth** — optional username/password gate for the whole UI

## Installation

### Raspberry Pi (real hardware)

```bash
sudo apt update && sudo apt install -y python3-venv espeak
git clone <your-repo> weather-station && cd weather-station
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

On first start the **setup wizard** opens automatically at
`http://<pi-ip>:8000/` (default sign-in `admin` / `admin` — change it in
`.env`). It walks you through:

1. **LCD pins** — RS, EN, D4–D7 (BCM numbering, must be unique)
2. **Sensors** — DHT11 data pin, button pin, buzzer pin
3. **Discord (optional)** — bot token, live-update & reminder channel IDs,
   admin role, weather image URL
4. **Review & save** — writes `.env`, mirrors pins into `config.py`, and
   creates any missing directories automatically

Then restart: `python main.py`. The wizard is **idempotent** — re-running
it (delete `.env` or visit `/setup`) updates the same keys in place and
pre-fills your current values.

#### Discord bot token setup (optional)

1. Open the [Discord Developer Portal](https://discord.com/developers/applications)
   → **New Application** → name it.
2. **Bot** tab → **Reset Token** → copy the token.
3. **Bot** tab → *Privileged Gateway Intents* → enable **MESSAGE CONTENT
   INTENT** (powers the "speak the weather" TTS listener).
4. **OAuth2 → URL Generator** → check `bot` + `applications.commands` →
   open the generated URL to invite the bot to your server.
5. Paste the token into the **setup wizard step 3** (or `DISCORD_BOT_TOKEN`
   in `.env`) and restart the station. Optionally add
   `DISCORD_UPDATE_CHANNEL_ID` (live weather cards),
   `DISCORD_REMINDER_CHANNEL_ID` (daily alarm reminders + boot status
   card), `DISCORD_ADMIN_ROLE` (admin command gate), and
   `DISCORD_WEATHER_IMAGE_URL` (card image).

Full details: the [Discord Guide](docs/discord-guide.md).

### Desktop / development (mock hardware)

Identical code paths run without GPIO — the LCD renders as `[SIMULATED]`,
sensors degrade gracefully, and the boot gate never blocks:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py            # → http://127.0.0.1:8000
```

### Docker (one command)

```bash
docker compose up -d      # → http://localhost:8000  (sign in admin/admin)
```

The container runs with mock hardware; SQLite persists in `./data/`.
Build only: `docker build -t weatherstation .` A `.dockerignore` keeps
venvs, logs, and databases out of the image context.

## Configuration

Everything is optional except the pins (wizard) — see `.env.example`:

| Feature | Configure with |
|---|---|
| Web sign-in | `WEB_AUTH_USERNAME` / `WEB_AUTH_PASSWORD` (default admin/admin), `WEB_AUTH_ENABLED=OFF` to disable |
| MQTT publishing | `MQTT_BROKER`, `MQTT_PORT`, `MQTT_TOPIC`, `MQTT_INTERVAL_S` — test via `POST /api/mqtt/publish` |
| Discord bot | `DISCORD_BOT_TOKEN` + optional `DISCORD_UPDATE_CHANNEL_ID`, `DISCORD_ADMIN_ROLE` |
| Voice Mode | Settings page toggle; `apt install espeak` (preferred) or `pip install pyttsx3` |
| Guest Mode | Settings page toggle; optional `LCD_CONTRAST_PIN=<bcm>` PWM wiring |
| Screen timeout | Settings page (30 s default, 0 = never) or `SCREEN_TIMEOUT_S` |
| Log compression | Settings toggle + `POST /api/archive-logs`; cutoff `LOG_ARCHIVE_AFTER_DAYS` (30) |
| Logging | `LOG_LEVEL` (DEBUG/INFO/WARNING/ERROR), `LOG_FILE` (rotating 5 MB × 5) |
| Database | `WEATHER_DB_PATH` (default `./weather_history.db`), host/port `WEATHER_HOST` / `WEATHER_PORT` |

**Frontend assets note:** Tailwind CSS and Chart.js load from their CDNs —
there is nothing to install for them. For a fully offline dashboard,
download `tailwind` and `chart.umd.min.js` once and serve them from
`web/static/` (paths are plain `<script>`/CSS tags you can repoint).

## Daily use

- **Tap** the button: next LCD page (Voice Mode: also speaks conditions)
- **Triple-tap**: physical settings menu (hold to modify, tap to advance)
- **Hold 5 s / 10 s**: reboot / shutdown
- **Web**: `/` dashboard · `/designer` LCD pages · `/logs` history &
  exports · `/settings` calibration & preferences
- **API**: `/api/data` `/api/history` `/api/system` `/api/health`
  `/api/notifications` `/api/export/all?format=json|csv` — all behind the
  same sign-in except `/api/health`

## Documentation

Full docs live in [`docs/`](docs/index.md):

- [User Manual](docs/user-manual.md) — install, first run, daily use, features, troubleshooting
- [Setup Guide](docs/setup-guide.md) — wiring, pin mapping, wizard walkthrough
- [Dashboard Guide](docs/dashboard-guide.md) — web UI, LCD mirror, notification center
- [Designer Guide](docs/designer-guide.md) — building LCD pages
- [Discord Guide](docs/discord-guide.md) — token setup, commands, live updates
- [API Reference](docs/api-reference.md) — every endpoint
- [Screenshots](docs/screenshots.md) — what each screen should look like

## Project layout

```
main.py              entry point: logging, supervisor, background loops, Uvicorn
config.py            pins, constants, AppState, health map, notifications
config_io.py         setup wizard persistence (.env + config.py, idempotent)
logging_setup.py     rotating-file logging (console + 5MB×5 file)
database.py          aiosqlite (WAL): logs, settings, pages, export, gzip archive
hardware/            lcd_driver.py (16×2 design system, mock) + sensors.py
services/            weather_api, render, moon_phase, discord_bot,
                     mqtt_client, voice, system_health
utils/               formatting helpers (clip/pad/center, unit conversion)
web/                 routes.py + templates/ (auth middleware, dashboard,
                     designer, logs, settings, setup wizard)
CHANGELOG.md         release history from v3.0 to latest
```

## Troubleshooting

- **LCD shows nothing**: check the wizard pins against your wiring; the
  contrast trim pot needs adjustment on most 1602A modules.
- **DHT11 reads fail**: verify the data pin and a 10k pull-up; the station
  keeps probing and self-heals when the sensor is reconnected.
- **Locked out of the web UI**: stop the app, edit `WEB_AUTH_USERNAME` /
  `WEB_AUTH_PASSWORD` in `.env`, or set `WEB_AUTH_ENABLED=OFF` and restart.
- **Logs**: `weather_station.log` (rotating) captures DEBUG+ for every
  subsystem; pass `LOG_LEVEL=DEBUG` for console verbosity.

See `CHANGELOG.md` for the full release history and `docs/` for the
complete documentation set.
