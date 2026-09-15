"""
routes.py — FastAPI application: API endpoints, UI routes, web server.

API:     /api/data, /api/history, /api/pages, /api/save-page,
         /api/delete-page, /api/widgets, /api/export-logs, /api/health
UI:      / (dashboard), /designer, /logs, /settings + POST actions
"""

from __future__ import annotations

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Form, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)

import config, config_io, database
from config import get_state
from services import moon_phase, render
from services import system_health
from utils import format_humid, format_temp, safe_float

log = logging.getLogger("weather.web")

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(title="Raspberry Pi Weather Station")
    _register_setup_routes(app)
    _register_api_routes(app)
    _register_ui_routes(app)
    return app


# ---------------------------------------------------------------------------
# First-time setup wizard
# ---------------------------------------------------------------------------

def _register_setup_routes(app: FastAPI) -> None:
    """Guided first-run wizard: pins + optional Discord token."""

    @app.get("/setup", response_class=HTMLResponse)
    async def setup_wizard():
        return _load_template("setup.html")

    @app.post("/setup/save")
    async def setup_save(request: Request):
        # Accept both JSON (fetch) and form-encoded (HTMX) submissions.
        content_type = request.headers.get("content-type", "")
        if "json" in content_type:
            body = await request.json()
        else:
            form = await request.form()
            body = {k: str(v) for k, v in form.items()}

        pin_keys = ["LCD_RS", "LCD_EN", "LCD_D4", "LCD_D5", "LCD_D6",
                    "LCD_D7", "DHT_PIN", "BUTTON_PIN", "BUZZER_PIN"]
        pins: Dict[str, int] = {}
        errors: Dict[str, str] = {}

        for key in pin_keys:
            raw = str(body.get(key, "")).strip()
            try:
                value = int(raw)
                if not (0 <= value <= 27):
                    raise ValueError
                pins[key] = value
            except (TypeError, ValueError):
                errors[key] = "BCM pin 0-27 required"

        if len(pins.values()) != len(set(pins.values())):
            errors["pins"] = "Each pin must be unique"

        if errors:
            return JSONResponse({"status": "error", "errors": errors},
                                status_code=400)

        token = str(body.get("DISCORD_BOT_TOKEN", "")).strip() or None
        channel = str(body.get("DISCORD_UPDATE_CHANNEL_ID", "")).strip() or None
        admin_role = str(body.get("DISCORD_ADMIN_ROLE", "")).strip() or None
        if channel and not channel.isdigit():
            return JSONResponse({"status": "error",
                                 "errors": {"DISCORD_UPDATE_CHANNEL_ID":
                                            "numeric channel ID required"}},
                                status_code=400)
        config_io.save_setup(pins, discord_token=token,
                             discord_channel_id=channel,
                             discord_admin_role=admin_role)
        return JSONResponse({"status": "success",
                             "message": "Setup saved — restart to apply"})


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

def _register_api_routes(app: FastAPI) -> None:
    @app.get("/api/data")
    async def get_live_data():
        state = get_state()
        pi_stats = render.get_pi_system_stats()
        phase_name, _, illum, _ = moon_phase.calculate_moon_phase()
        unit = state.get_setting("unit")
        return JSONResponse({
            "indoor_temp": format_temp(state.indoor_temp, unit),
            "indoor_humid": format_humid(state.indoor_humid),
            "outdoor_temp": format_temp(state.outdoor_temp, unit),
            "outdoor_humid": format_humid(safe_float(state.outdoor_humid)),
            "outdoor_min": format_temp(state.outdoor_min, unit),
            "outdoor_max": format_temp(state.outdoor_max, unit),
            "uv_current": state.uv_current,
            "uv_max": state.uv_max,
            "aqi": state.aqi_val,
            "aqi_status": state.aqi_status,
            "pm2_5": state.pm2_5_val,
            "pm10": state.pm10_val,
            "weather_text": render.weather_info(state.weather_code)[1],
            "moon_phase": phase_name,
            "moon_illumination": f"{illum}%",
            "comfort": render.get_comfort_level(
                state.indoor_temp, state.indoor_humid),
            "dht_status": "ONLINE" if not state.dht_error else "OFFLINE / ERROR",
            "wifi_status": "CONNECTED" if not state.wifi_error else "DISCONNECTED",
            "pi_cpu_temp": pi_stats["cpu_temp"],
            "pi_cpu_usage": pi_stats["cpu_usage"],
            "pi_ram_usage": pi_stats["ram_usage"],
            "lcd_line1": state.last_lcd_rendered_text[0],
            "lcd_line2": state.last_lcd_rendered_text[1],
            "current_page": state.current_page,
            "lcd_mock": get_lcd_mock_flag(),
            "guest_active": state.guest_active,
            "voice_mode": state.get_setting("voice_mode"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "subsystems": config.subsystem_status(),
        })

    @app.get("/api/history")
    async def get_history(limit: int = 200):
        rows = await database.fetch_history_for_chart(limit=min(limit, 1000))
        return JSONResponse({"history": rows})

    @app.get("/api/widgets")
    async def get_widgets():
        return JSONResponse({"widgets": render.WIDGET_CATALOG})

    @app.get("/api/widgets/preview")
    async def widget_preview(type: str):
        """Render one widget frame server-side for the designer simulation box."""
        frame = render.render_widget_page(type)
        if frame is None:
            return JSONResponse({"error": "unknown widget"}, status_code=404)
        return JSONResponse({"line1": frame[0], "line2": frame[1]})

    @app.post("/api/rename-page")
    async def rename_page(request: Request):
        """Designer: rename an LCD page tab (persisted in page_meta)."""
        state = get_state()
        try:
            body = await request.json()
            page_id = int(body.get("page_id", 0))
            name = str(body.get("name", "")).strip()
        except Exception:
            return JSONResponse({"status": "error",
                                 "message": "invalid request"}, status_code=400)
        if not (1 <= page_id <= config.MAX_LCD_PAGES):
            return JSONResponse({"status": "error",
                                 "message": "bad page_id"}, status_code=400)
        name = name[:16] or config.PAGE_NAMES.get(page_id, f"Page {page_id}")
        state.page_names[page_id] = name
        await database.rename_page(page_id, name)
        return JSONResponse({"status": "success", "page_id": page_id,
                             "name": name})

    @app.get("/api/pages/full")
    async def get_pages_full():
        """Pages + names + current widget assignment for the designer tabs."""
        state = get_state()
        pages = []
        for page_id in range(1, state.total_pages + 1):
            pages.append({
                "page_id": page_id,
                "name": state.page_names.get(
                    page_id, config.PAGE_NAMES.get(page_id, f"Page {page_id}")),
                "widget": state.custom_lcd_pages.get(page_id),
            })
        return JSONResponse({"pages": pages})

    @app.get("/api/pages")
    async def get_pages():
        return JSONResponse(get_state().custom_lcd_pages)

    @app.post("/api/save-page")
    async def save_page(request: Request):
        state = get_state()
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"status": "error",
                                 "message": "invalid JSON"}, status_code=400)

        try:
            page_id = int(body.get("page_id", 0))
        except (TypeError, ValueError):
            return JSONResponse({"status": "error",
                                 "message": "bad page_id"}, status_code=400)

        widget_type = str(body.get("widget_type", "")).strip()
        if not widget_type:
            return JSONResponse({"status": "error",
                                 "message": "widget_type required"},
                                status_code=400)

        if not (1 <= page_id <= config.MAX_LCD_PAGES):
            return JSONResponse({"status": "error",
                                 "message": f"page_id must be 1..{config.MAX_LCD_PAGES}"},
                                status_code=400)

        if (widget_type not in render.WIDGET_REGISTRY
                and not _is_valid_custom_block(widget_type)):
            return JSONResponse({"status": "error",
                                 "message": "unknown widget_type"},
                                status_code=400)

        state.custom_lcd_pages[page_id] = widget_type
        if page_id > state.total_pages:
            state.total_pages = page_id
        if body.get("activate"):
            # Designer "Apply & Save": jump the physical LCD to this page
            # immediately so the change is visible in real time.
            state.current_page = page_id
        state.mark_page_dirty()

        await database.save_custom_page(page_id, widget_type)
        return JSONResponse({"status": "success", "page_id": page_id,
                             "widget": widget_type})

    @app.post("/api/delete-page")
    async def delete_page(request: Request):
        state = get_state()
        try:
            body = await request.json()
            page_id = int(body.get("page_id", 0))
        except Exception:
            return JSONResponse({"status": "error",
                                 "message": "invalid request"}, status_code=400)

        if page_id <= config.BASE_PAGE_COUNT:
            return JSONResponse({"status": "error",
                                 "message": "pages 1-6 are core pages"},
                                status_code=400)

        state.custom_lcd_pages.pop(page_id, None)
        state.total_pages = max(
            config.BASE_PAGE_COUNT,
            max(state.custom_lcd_pages.keys(), default=config.BASE_PAGE_COUNT),
        )
        state.mark_page_dirty()
        await database.delete_custom_page(page_id)
        return JSONResponse({"status": "deleted", "page_id": page_id})

    @app.post("/api/import-layout")
    async def import_layout(request: Request):
        """Designer: bulk-apply an exported layout JSON.

        Body: {"pages": {"<page_id>": widget_type, ...},
               "names": {"<page_id>": name, ...}}
        Invalid entries are skipped and reported; valid ones persist.
        """
        state = get_state()
        try:
            body = await request.json()
            pages_in = body.get("pages") or {}
            names_in = body.get("names") or {}
            if not isinstance(pages_in, dict):
                raise ValueError("pages must be an object")
            if not isinstance(names_in, dict):
                names_in = {}
        except Exception:
            return JSONResponse({"status": "error",
                                 "message": "invalid JSON"}, status_code=400)

        applied: list = []
        errors: Dict[str, str] = {}

        for raw_id, widget in pages_in.items():
            try:
                page_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if not (1 <= page_id <= config.MAX_LCD_PAGES):
                errors[str(raw_id)] = "page out of range"
                continue
            widget = str(widget)
            if (widget not in render.WIDGET_REGISTRY
                    and not _is_valid_custom_block(widget)):
                errors[str(raw_id)] = "unknown widget_type"
                continue
            state.custom_lcd_pages[page_id] = widget
            applied.append(page_id)

        for raw_id, name in names_in.items():
            try:
                page_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            clean = str(name).strip()[:16]
            if 1 <= page_id <= config.MAX_LCD_PAGES and clean:
                state.page_names[page_id] = clean
                await database.rename_page(page_id, clean)

        for page_id in applied:
            await database.save_custom_page(
                page_id, state.custom_lcd_pages[page_id])

        if applied:
            state.total_pages = max(
                config.BASE_PAGE_COUNT,
                max(state.custom_lcd_pages.keys(), default=0),
            )
            state.mark_page_dirty()

        return JSONResponse({
            "status": "success" if applied else "error",
            "applied": applied,
            "errors": errors,
        }, status_code=200 if applied else 400)

    @app.get("/api/export-logs")
    async def export_logs_csv():
        csv_text = await database.export_all_logs_csv()
        return PlainTextResponse(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition":
                     "attachment; filename=weather_logs.csv"},
        )

    @app.get("/api/system")
    async def get_system_health():
        """ENH 1: full system health snapshot for the dashboard card."""
        snapshot = system_health.collect_system_health()
        snapshot["lcd_mock"] = get_lcd_mock_flag()
        return JSONResponse(snapshot)

    @app.get("/api/notifications")
    async def get_notifications(limit: int = 25):
        """ENH 2: notification center feed (newest first)."""
        items = config.get_notifications(limit=min(limit, 50))
        return JSONResponse({
            "notifications": items,
            "count": len(items),
            "unread": len(items),
        })

    @app.post("/api/notifications/clear")
    async def notifications_clear():
        """ENH 2: dismiss all notifications (bell icon)."""
        config.clear_notifications()
        return JSONResponse({"status": "cleared"})

    @app.post("/api/mqtt/publish")
    async def mqtt_publish_test():
        """ENH 3: one-shot publish for testing the broker connection."""
        from services import mqtt_client
        if not config.MQTT_BROKER:
            return JSONResponse({
                "status": "error",
                "message": "MQTT_BROKER not configured (set it in .env)",
            }, status_code=400)
        ok = await asyncio.get_event_loop().run_in_executor(
            None, mqtt_client.publish_snapshot)
        if ok:
            config.push_notification(
                "info", f"MQTT test publish sent to {config.MQTT_BROKER}")
        return JSONResponse({
            "status": "success" if ok else "error",
            "broker": config.MQTT_BROKER,
            "port": config.MQTT_PORT,
            "topic": config.MQTT_TOPIC,
            "payload": mqtt_client.build_snapshot(),
        }, status_code=200 if ok else 502)

    @app.get("/api/export/all")
    async def export_all_data(format: str = "json"):
        """ENH 6: full SQLite history + settings as CSV or JSON download."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if format == "csv":
            csv_text = await database.export_all_data_csv()
            return PlainTextResponse(
                content=csv_text,
                media_type="text/csv",
                headers={"Content-Disposition":
                         f"attachment; filename=weatherstation_full_{stamp}.csv"},
            )
        payload = await database.export_all_data()
        return JSONResponse(
            content=payload,
            headers={"Content-Disposition":
                     f"attachment; filename=weatherstation_full_{stamp}.json"},
        )

    @app.get("/api/health")
    async def health():
        state = get_state()
        return JSONResponse({
            "status": "ok",
            "subsystems": config.subsystem_status(),
            "lcd_mock": get_lcd_mock_flag(),
            "dht_error": state.dht_error,
            "wifi_error": state.wifi_error,
        })


def _is_valid_custom_block(widget_type: str) -> bool:
    """Accept {"type":"custom","lines":[...]} JSON blocks."""
    try:
        data = json.loads(widget_type)
    except (json.JSONDecodeError, TypeError):
        return False
    return (isinstance(data, dict)
            and data.get("type") == "custom"
            and isinstance(data.get("lines"), list)
            and len(data["lines"]) >= 1)


def get_lcd_mock_flag() -> bool:
    """True when the LCD backend is the desktop mock (drives the UI badge)."""
    try:
        from hardware.lcd_driver import get_lcd
        return get_lcd().is_mock
    except Exception:
        return True


# ---------------------------------------------------------------------------
# UI routes (serve modern templates)
# ---------------------------------------------------------------------------

def _register_ui_routes(app: FastAPI) -> None:
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        # First run: send the user to the guided setup wizard.
        if config_io.first_run_needed():
            return RedirectResponse(url="/setup", status_code=302)
        return _load_template("dashboard.html")

    @app.get("/designer", response_class=HTMLResponse)
    async def designer():
        if config_io.first_run_needed():
            return RedirectResponse(url="/setup", status_code=302)
        return _load_template("designer.html")

    @app.get("/partials/trend", response_class=HTMLResponse)
    async def trend_partial():
        """HTMX partial: chart data <script> + history table, polled 30s."""
        rows = await database.fetch_history_for_chart(limit=200)
        payload = json.dumps(rows, default=str)
        return _load_template("partials/trend.html").replace(
            "__TREND_DATA__", payload)

    @app.get("/logs", response_class=HTMLResponse)
    async def logs_page():
        rows, total = await database.fetch_logs_page(limit=100)
        html = _load_template("logs.html")
        body_rows = "".join(
            f"<tr class='hover:bg-slate-700/40 transition-colors'>"
            f"<td class='px-4 py-2'>#{r[0]}</td>"
            f"<td class='px-4 py-2'>{r[1]}</td>"
            f"<td class='px-4 py-2'>{r[2] if r[2] is not None else '—'}</td>"
            f"<td class='px-4 py-2'>{r[3] if r[3] is not None else '—'}</td>"
            f"<td class='px-4 py-2'>{r[4] if r[4] is not None else '—'}</td>"
            f"<td class='px-4 py-2'>{r[5] if r[5] is not None else '—'}</td>"
            f"</tr>"
            for r in rows
        ) or ("<tr><td colspan='6' class='px-4 py-8 text-center text-slate-400'>"
              "No log records found.</td></tr>")
        return html.replace("{{ total_count }}", str(total)) \
                   .replace("{{ table_rows }}", body_rows)

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page():
        state = get_state()
        html = _load_template("settings.html")
        return _render_settings(html, state)

    # -- POST actions ------------------------------------------------------

    @app.post("/update-location")
    async def update_location(
        latitude: str = Form(...), longitude: str = Form(...)
    ):
        state = get_state()
        state.set_setting("latitude", latitude.strip())
        state.set_setting("longitude", longitude.strip())
        state.mark_page_dirty()
        await database.save_setting("latitude", latitude.strip())
        await database.save_setting("longitude", longitude.strip())
        return RedirectResponse(url="/settings", status_code=303)

    @app.post("/update-settings")
    async def update_settings(
        unit: str = Form(...),
        buzzer: str = Form(...),
        screen: str = Form(...),
        auto_scroll: int = Form(...),
        alarm_on: str = Form(...),
        alarm_hr: int = Form(...),
        alarm_min: int = Form(...),
        api_rate: int = Form(...),
        log_rate: int = Form(...),
        voice_mode: str = Form("OFF"),
        guest_mode: str = Form("OFF"),
    ):
        state = get_state()
        for key, value in {
            "unit": unit, "buzzer": buzzer, "screen": screen,
            "auto_scroll": auto_scroll, "alarm_on": alarm_on,
            "alarm_hr": alarm_hr, "alarm_min": alarm_min,
            "api_rate": api_rate, "log_rate": log_rate,
            "voice_mode": voice_mode, "guest_mode": guest_mode,
        }.items():
            state.set_setting(key, value)
            await database.save_setting(key, value)
        state.mark_page_dirty()
        return RedirectResponse(url="/settings", status_code=303)

    @app.post("/calibrate-dht")
    async def calibrate_dht():
        state = get_state()
        if (state.indoor_temp_raw is not None
                and state.outdoor_temp != "N/A"):
            try:
                target = float(state.outdoor_temp)
                offset = round(target - state.indoor_temp_raw, 1)
                state.set_setting("dht_offset_temp", offset)
                state.indoor_temp = round(state.indoor_temp_raw + offset, 1)
                state.mark_page_dirty()
                await database.save_setting("dht_offset_temp", offset)
            except ValueError:
                pass
        return RedirectResponse(url="/settings", status_code=303)

    @app.post("/reset-dht")
    async def reset_dht():
        state = get_state()
        state.set_setting("dht_offset_temp", 0.0)
        if state.indoor_temp_raw is not None:
            state.indoor_temp = round(state.indoor_temp_raw, 1)
        state.mark_page_dirty()
        await database.save_setting("dht_offset_temp", 0.0)
        return RedirectResponse(url="/settings", status_code=303)

    @app.post("/clear-logs")
    async def clear_logs():
        await database.clear_all_logs()
        return RedirectResponse(url="/logs", status_code=303)

    @app.post("/factory-reset")
    async def factory_reset():
        state = get_state()
        await database.perform_factory_reset(state)
        return RedirectResponse(url="/settings", status_code=303)


# ---------------------------------------------------------------------------
# Settings template renderer
# ---------------------------------------------------------------------------

def _voice_backend_hint() -> str:
    """ENH 4: warn when Voice Mode has no TTS backend installed."""
    try:
        from services.voice import is_configured
        return "" if is_configured() else \
            "No TTS backend found — install espeak (apt) or pyttsx3 (pip)."
    except Exception:
        return ""


def _render_settings(html: str, state) -> str:
    """Populate the settings template tokens from live state."""
    unit = state.get_setting("unit")
    buzzer = state.get_setting("buzzer")
    screen = state.get_setting("screen")
    scroll = int(state.get_setting("auto_scroll"))
    alarm_on = state.get_setting("alarm_on")
    api_rate = int(state.get_setting("api_rate"))
    log_rate = int(state.get_setting("log_rate"))
    voice_mode = state.get_setting("voice_mode")
    guest_mode = state.get_setting("guest_mode")
    raw = state.indoor_temp_raw
    offset = float(state.get_setting("dht_offset_temp") or 0.0)
    calibrated = (round(raw + offset, 1) if raw is not None else None)
    unit_now = state.get_setting("unit")

    def sel(flag: bool) -> str:
        return "selected" if flag else ""

    replacements = {
        "{{ latitude }}": str(state.get_setting("latitude")),
        "{{ longitude }}": str(state.get_setting("longitude")),
        "{{ raw_temp }}": f"{raw:.1f} C" if raw is not None else "N/A",
        "{{ offset }}": f"{offset:+.1f} C",
        "{{ calibrated }}": format_temp(calibrated, unit_now),
        "{{ outdoor }}": format_temp(state.outdoor_temp, unit_now),
        "{{ alarm_hr }}": str(state.get_setting("alarm_hr")),
        "{{ alarm_min }}": str(state.get_setting("alarm_min")),
        "{{ sel_unit_C }}": sel(unit == "C"),
        "{{ sel_unit_F }}": sel(unit == "F"),
        "{{ sel_buzzer_ALL }}": sel(buzzer == "ALL"),
        "{{ sel_buzzer_ERR }}": sel(buzzer == "ERR"),
        "{{ sel_buzzer_MUTE }}": sel(buzzer == "MUTE"),
        "{{ sel_screen_ON }}": sel(screen == "ON"),
        "{{ sel_screen_OFF }}": sel(screen == "OFF"),
        "{{ sel_scroll_0 }}": sel(scroll == 0),
        "{{ sel_scroll_3 }}": sel(scroll == 3),
        "{{ sel_scroll_5 }}": sel(scroll == 5),
        "{{ sel_scroll_10 }}": sel(scroll == 10),
        "{{ sel_alarm_on_ON }}": sel(alarm_on == "ON"),
        "{{ sel_alarm_on_OFF }}": sel(alarm_on == "OFF"),
        "{{ sel_api_5 }}": sel(api_rate == 5),
        "{{ sel_api_10 }}": sel(api_rate == 10),
        "{{ sel_api_15 }}": sel(api_rate == 15),
        "{{ sel_log_5 }}": sel(log_rate == 5),
        "{{ sel_log_15 }}": sel(log_rate == 15),
        "{{ sel_log_30 }}": sel(log_rate == 30),
        "{{ sel_voice_ON }}": sel(voice_mode == "ON"),
        "{{ sel_voice_OFF }}": sel(voice_mode == "OFF"),
        "{{ sel_guest_ON }}": sel(guest_mode == "ON"),
        "{{ sel_guest_OFF }}": sel(guest_mode == "OFF"),
        "{{ voice_backend_hint }}": _voice_backend_hint(),
    }
    for token, value in replacements.items():
        html = html.replace(token, value)
    return html


# ---------------------------------------------------------------------------
# Server bootstrap (invoked from main.py inside the running loop)
# ---------------------------------------------------------------------------

async def run_web_server() -> None:
    import uvicorn

    app = create_app()
    uvicorn_config = uvicorn.Config(
        app=app,
        host=config.HOST,
        port=config.PORT,
        log_level="warning",
    )
    server = uvicorn.Server(uvicorn_config)
    await server.serve()
