# Raspberry Pi Weather Station — Documentation

Welcome to the official documentation for the **Raspberry Pi Weather
Station**: a 1602A LCD station with a DHT11 sensor, buzzer & tap button, a
Tailwind dark-glass web dashboard, an LCD page designer, a Discord bot, MQTT
publishing, voice mode, and a self-healing async core.

## Documentation map

| Document | Contents |
|---|---|
| [User Manual](user-manual.md) | The complete manual: install, first run, daily use, every feature |
| [Setup Guide](setup-guide.md) | Hardware wiring, pin mapping, and the first-run setup wizard step by step |
| [Dashboard Guide](dashboard-guide.md) | Web dashboard, LCD mirror, charts, notification center, settings |
| [Designer Guide](designer-guide.md) | Building LCD pages: widgets, simulator, thumbnails, JSON import/export |
| [Discord Guide](discord-guide.md) | Bot token setup, slash commands, live updates, alarm reminders, images |
| [API Reference](api-reference.md) | Every HTTP endpoint with request/response examples |
| [Screenshots](screenshots.md) | Descriptions of every UI screen (what you should see) |

## The 60-second version

```bash
# 1. Install (Raspberry Pi OS / Debian)
sudo apt update && sudo apt install -y python3-venv espeak
git clone <your-repo> weather-station && cd weather-station
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Run
python main.py
```

3. Open `http://<pi-ip>:8000/` — you are redirected to the **setup wizard**.
4. Enter your LCD + sensor pins (and optionally your Discord bot token).
5. Save, restart the station, and you are live.

Default web sign-in is `admin` / `admin` — change it in `.env`
(`WEB_AUTH_USERNAME` / `WEB_AUTH_PASSWORD`) before exposing the station to
your network.

## Where to go next

- Wiring your LCD and DHT11? → [Setup Guide](setup-guide.md)
- Want the bot to post weather cards to Discord? → [Discord Guide](discord-guide.md)
- Curious what a widget does? → [Designer Guide](designer-guide.md)
- Scripting against the station? → [API Reference](api-reference.md)
- Something broken? → Troubleshooting in the [User Manual](user-manual.md)
