# Changelog

All notable changes to the Raspberry Pi Weather Station.
Format: [version] — date — highlights.

## [5.1] — 2026-09-15 — Enhancement Pack 1

### Added (Discord Bot)
- **New slash commands**: `/forecast` (min/max, UV, conditions),
  `/alarm-on` / `/alarm-off`, `/set-alert high low` (user-configurable
  indoor alert thresholds, enforced by the DHT poller), `/status-embed`
  (weather + system all-in-one card), and `/liveupdate on|off [channel]`.
- **Voice replies**: saying "speak the weather" in a channel the bot can
  see makes it reply with a Discord-TTS spoken temperature summary.
- **Live updates**: a weather card is posted to the configured channel
  whenever the data signature changes (rate-limited; alarm/alert
  transitions bypass the limit). Channel set via the setup wizard or
  `/liveupdate`.
- **Role-based permissions**: admin commands (setpage, alarm, set-alert,
  liveupdate) require the Administrator permission or the role named by
  `DISCORD_ADMIN_ROLE` (setup wizard / `.env`).
- **Weather card embed**: rich card with moon-phase emoji, formatted
  temps, AQI-colored accent, LCD page, and version footer.

### Added (UI Designer)
- **Quick Add** button on every widget card: one click selects, saves, and
  applies the widget to the current page with a confirmation toast.
- **Page preview thumbnails**: live 16×2 miniatures for every page 1–10,
  rendered server-side and clickable to open the page.
- **Full custom-character support** in the LCD simulator: all eight
  glyphs (\x00–\x07) render as distinct icons with tooltips, in both the
  main simulator and the thumbnails.
- **Clone Page** (widget + name copied to a target page) and a
  **Rename Page** button (in addition to tab double-click).
- **Export/Import Layout JSON**: downloads + clipboard copy of the full
  page map and tab names; file-picker import applies via a validating
  bulk endpoint (`POST /api/import-layout`) that skips invalid entries.
- **Apply & Save** now also activates the page on the physical LCD
  (`activate: true` on `/api/save-page`) and confirms with a toast.

### Added
- **System Health Dashboard**: homepage card with CPU temp, CPU load, RAM,
  disk usage, IP address, uptime, and WiFi signal strength (`iwconfig`
  fallback `nmcli`), refreshed every 10s via `/api/system`.
- **Notification Center**: bell icon in the navbar; captures temp alerts,
  daily alarm triggers, subsystem crashes, and MQTT/Guest Mode events.
  Feed at `/api/notifications`, clear via `/api/notifications/clear`.
- **MQTT publishing** (`paho-mqtt`): set `MQTT_BROKER` in `.env` to enable;
  publishes a JSON snapshot to `MQTT_TOPIC` every `MQTT_INTERVAL_S`.
  Test endpoint: `POST /api/mqtt/publish`.
- **Voice Mode** (settings toggle): speaks indoor/outdoor temps on a button
  tap and announces temperature shifts ≥ 2 °C. Backends: `espeak`
  (preferred) or `pyttsx3`; UI warns when no backend is installed.
- **Guest Mode** (settings toggle): after 30 minutes without a button press
  the LCD contrast dims (PWM on optional `LCD_CONTRAST_PIN`, backlight
  fallback otherwise) and the buzzer stays silent; data keeps rendering.
  Any press restores instantly.
- **Export All Data**: logs page buttons for full-history CSV and a JSON
  bundle containing logs + settings + UI pages + page names
  (`GET /api/export/all?format=json|csv`).
- **Docker support**: `Dockerfile` + `docker-compose.yml` for one-command
  container runs (`docker compose up`); mock hardware mode on desktop.

### Changed
- Default `WEATHER_DB_PATH` now resolves inside the project directory
  (was the hardcoded `/home/admin/weather_history.db`).
- Flat project layout: `main.py`, `config.py`, `config_io.py`,
  `database.py` at repo root with `hardware/`, `services/`, `utils/`,
  `web/` packages — the `weather_station/` wrapper package was removed
  and all imports rewritten.

## [5.0] — 2026-09-15 — Setup Wizard, Discord, Polish

### Added
- First-Time Setup Wizard (`/setup`): guided pin mapping + optional Discord
  bot token; writes `.env` and mirrors pins into `config.py`.
- Discord bot with `/weather`, `/setpage`, `/alarm`, `/status` slash
  commands and rich embeds.
- `.env.example`, graceful-shutdown runtime snapshot (page, settings,
  page names persisted on Ctrl+C), `ensure_directories()` scaffolding.
- `LCD_CONTRAST_PIN` env key for optional contrast PWM wiring.
- `clip_text` / `pad_text` / `center_text` helpers wired into every LCD
  render path (strict 16-char guarantee).

### Changed
- Version bumped to 5.0; setup wizard completion flag tracked in config.

## [4.1] — 2026-09-15 — Modular Rebuild

### Changed
- Monolithic 1,679-line `weather_station.py` split into a supervised
  multi-module architecture: config / database / hardware / services /
  utils / web with a `safe_task` supervisor (cool-down restarts, health
  map surfaced via `/api/health`).
- Tailwind dark-glass dashboard with Chart.js indoor-vs-outdoor trends,
  HTMX 30s partial refresh, and a pixel-perfect 16×2 designer simulator
  with green/blue themes, drag-and-drop widgets, and renameable tabs.
- Burn-once CGRAM glyphs (\x00–\x07): created once at startup, never
  re-created at runtime (thread-safe, render-cycle safe).
