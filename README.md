# Raspberry Pi Weather Station

A modular weather station: 1602A LCD, DHT11 sensor, buzzer & button on a
Raspberry Pi, with a Tailwind dark-glass web dashboard, UI page designer,
Discord bot, MQTT publishing, and a supervised async core.

## How to build & run

### Bare metal (Raspberry Pi — real hardware)

```bash
pip install -r requirements.txt
python main.py
```

First run opens the setup wizard at `http://<pi-ip>:8000/setup` — map your
LCD/DHT/button/buzzer pins (and optionally paste a Discord bot token), then
restart. On subsequent runs the dashboard is served at
`http://<pi-ip>:8000`.

### Desktop (mock hardware, same code paths)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py            # LCD runs as [SIMULATED], no GPIO needed
```

### Docker (one command)

```bash
docker compose up -d      # → http://localhost:8000
```

The container runs with mock hardware; the SQLite database persists in
`./data/`. Build only: `docker build -t weatherstation .`

### Optional integrations (`.env`, see `.env.example`)

| Feature | Enable with |
|---|---|
| MQTT publishing | `MQTT_BROKER=<ip>` — test via `POST /api/mqtt/publish` |
| Discord bot | `DISCORD_BOT_TOKEN=...` (or via the setup wizard) |
| Voice Mode | Settings page toggle + `apt install espeak` (or `pip install pyttsx3`) |
| Guest Mode dimming | Settings page toggle + optional `LCD_CONTRAST_PIN=<bcm>` PWM |

## Layout

```
main.py              entry point: supervisor, background loops, Uvicorn
config.py            pins, constants, AppState, health map, notifications
config_io.py         setup wizard persistence (.env + config.py)
database.py          aiosqlite: logs, settings, pages, full export
hardware/            lcd_driver.py (16x2 design system, mock) + sensors.py
services/            weather_api, render, moon_phase, discord_bot,
                     mqtt_client, voice, system_health
utils/               formatting helpers (clip/pad/center, formatters)
web/                 routes.py + templates/ (dashboard, designer, ...)
```

See `CHANGELOG.md` for release history.
