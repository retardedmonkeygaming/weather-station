# API Reference

Base URL: `http://<station-ip>:8000`. Every route requires web basic auth
(`WEB_AUTH_USERNAME` / `WEB_AUTH_PASSWORD`, default `admin` / `admin`)
**except** `GET /api/health`, which stays open for liveness probes.

---

## Live data

### `GET /api/health`

Liveness probe (no auth).

```json
{"status": "ok", "subsystems": {}, "lcd_mock": true,
 "dht_error": false, "wifi_error": false}
```

`subsystems` maps any currently-failing supervised task to its error and
restart count.

### `GET /api/data`

The dashboard's main poll (flat payload):

| Key | Meaning |
|---|---|
| `indoor_temp` / `indoor_humid` | DHT11 readings, unit-aware (`"23.5C"`) |
| `outdoor_temp` / `outdoor_humid` / `outdoor_min` / `outdoor_max` | Open-Meteo values (frozen in Local Mode) |
| `uv_current` / `uv_max` | UV index now / today's peak |
| `aqi` / `aqi_status` / `pm2_5` / `pm10` | Air quality block |
| `weather_text` / `moon_phase` / `moon_illumination` / `comfort` | Derived values |
| `dht_status` / `wifi_status` | `ONLINE`/`OFFLINE`, `CONNECTED`/`DISCONNECTED` |
| `pi_cpu_temp` / `pi_cpu_usage` / `pi_ram_usage` | Pi diagnostics |
| `lcd_line1` / `lcd_line2` | The exact 16-char rows the physical LCD received |
| `current_page` / `lcd_mock` / `guest_active` / `local_mode` / `voice_mode` / `unit` | UI state |
| `time` / `date` | Station clock |
| `subsystems` | Failing subsystems map |

## History & exports

| Endpoint | Description |
|---|---|
| `GET /api/history?limit=200` | Oldest-first chart rows `{timestamp, in_temp, out_temp, in_humid, out_humid}` |
| `GET /api/export-logs` | Full `weather_logs` CSV download |
| `GET /api/export/all?format=json` | Entire DB bundle: logs, settings, ui_pages, page_meta |
| `GET /api/export/all?format=csv` | Full log history as CSV |
| `POST /api/archive-logs` | gzip rows older than `LOG_ARCHIVE_AFTER_DAYS` (30); returns archived count + filename |

## System

| Endpoint | Description |
|---|---|
| `GET /api/system` | Health card: CPU temp/usage, RAM, disk, IP, uptime, WiFi signal, version |
| `GET /api/notifications?limit=25` | Bell feed (newest first) `{notifications:[{ts,kind,message}], count}` |
| `POST /api/notifications/clear` | Empty the bell |

## Pages & designer

| Endpoint | Description |
|---|---|
| `GET /api/widgets` | Widget catalog `{type, icon, title, desc}` |
| `GET /api/widgets/preview?type=widget_moon` | Server-side render `{line1, line2}` for the simulator/thumbnails |
| `GET /api/pages` | `{page_id: widget_type}` map |
| `GET /api/pages/full` | Pages + names + widget for the designer tabs |
| `POST /api/save-page` | Body `{page_id, widget_type, activate?}`; `activate:true` jumps the physical LCD to the page |
| `POST /api/rename-page` | Body `{page_id, name}` (≤16 chars) |
| `POST /api/delete-page` | Body `{page_id}` (core pages 1–6 rejected) |
| `POST /api/import-layout` | Body `{pages:{...}, names:{...}}`; applies valid entries, reports skipped ones |

## Integrations

| Endpoint | Description |
|---|---|
| `POST /api/mqtt/publish` | One-shot broker publish (400 if `MQTT_BROKER` unset, 502 on broker failure) |
| `GET /api/ping` | Dynamic display: flash the "WebUI Connected!" banner on the LCD once |

## UI routes

| Route | Description |
|---|---|
| `GET /` | Dashboard (redirects to `/setup` before first configuration) |
| `GET /setup` | Setup wizard — always reachable; pre-fills saved values in Reconfigure mode |
| `POST /setup/save` | Wizard persistence (JSON or form): pins + Discord keys → `.env` (+ `config.py` mirror), idempotent |
| `POST /update-pins` | Settings pin editor; same validation, reports changed pins |
| `GET /designer` `/logs` `/settings` | UI pages |
| `GET /partials/trend` | HTMX chart/table partial |
| `POST /update-location` `/update-settings` | Settings forms (303 back to `/settings`) |
| `POST /run-backup` | Manual full backup into `backups/backup_YYYY-MM-DD/` |
| `POST /calibrate-dht` `/reset-dht` | DHT11 offset calibration |
| `POST /clear-logs` `/factory-reset` | Danger-zone actions |

### Example: save + activate a page

```bash
curl -u admin:admin -X POST http://<ip>:8000/api/save-page \
  -H 'Content-Type: application/json' \
  -d '{"page_id": 4, "widget_type": "widget_forecast", "activate": true}'
```
