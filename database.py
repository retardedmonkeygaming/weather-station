"""
database.py — aiosqlite persistence layer.

Owns:
    * Connection lifecycle (shared cached connection, safe init/shutdown).
    * Table schema creation (weather_logs, settings, ui_pages).
    * Historical environmental logs (insert, query, export, purge).
    * Settings persistence (load merged over defaults, upsert single key).
    * Custom LCD page layout saving/loading (ui_pages table).
"""

from __future__ import annotations

import asyncio
import csv
import gzip
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import aiosqlite

import config

log = logging.getLogger("weather.db")

_weather_logs_table = """
    CREATE TABLE IF NOT EXISTS weather_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        in_temp REAL, in_humid REAL,
        out_temp REAL, out_humid REAL
    )
"""
_settings_table = """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
"""
_ui_pages_table = """
    CREATE TABLE IF NOT EXISTS ui_pages (
        page_id INTEGER PRIMARY KEY,
        layout_json TEXT
    )
"""
_page_meta_table = """
    CREATE TABLE IF NOT EXISTS page_meta (
        page_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    )
"""

_conn: Optional[aiosqlite.Connection] = None
_write_lock = asyncio.Lock()


async def get_connection() -> aiosqlite.Connection:
    """Return the shared aiosqlite connection, opening it lazily."""
    global _conn
    if _conn is None:
        Path(config.DB_FILE).parent.mkdir(parents=True, exist_ok=True)
        _conn = await aiosqlite.connect(config.DB_FILE)
        await _conn.execute("PRAGMA journal_mode=WAL")
    return _conn


async def close() -> None:
    """Close the shared connection (called on shutdown)."""
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Create tables if missing and enable WAL journaling."""
    db = await get_connection()
    async with _write_lock:
        await db.execute(_weather_logs_table)
        await db.execute(_settings_table)
        await db.execute(_ui_pages_table)
        await db.execute(_page_meta_table)
        await db.commit()
    log.info("Database ready at %s", config.DB_FILE)


# ---------------------------------------------------------------------------
# Settings persistence
# ---------------------------------------------------------------------------

async def load_settings(state) -> None:
    """Load persisted settings into AppState, merged over defaults."""
    db = await get_connection()
    loaded: Dict[str, str] = {}
    try:
        async with db.execute("SELECT key, value FROM settings") as cursor:
            async for key, value in cursor:
                loaded[key] = value

        for key, raw in loaded.items():
            if key not in config.SETTINGS_DEFAULTS:
                continue
            coerce = config.SETTINGS_TYPES.get(key, str)
            try:
                state.set_setting(key, coerce(raw))
            except (TypeError, ValueError):
                log.warning("Bad value for setting %r: %r — kept default", key, raw)

        if state.get_setting("alarm_min") > 59:
            state.set_setting("alarm_min", 59)

        state.custom_lcd_pages.clear()
        async with db.execute("SELECT page_id, layout_json FROM ui_pages") as cursor:
            async for page_id, layout_json in cursor:
                state.custom_lcd_pages[int(page_id)] = str(layout_json)

        if state.custom_lcd_pages:
            highest = max(state.custom_lcd_pages.keys())
            state.total_pages = max(config.BASE_PAGE_COUNT, highest)

        log.info(
            "Loaded %d settings, %d custom pages",
            len(loaded), len(state.custom_lcd_pages),
        )
    except Exception:
        log.exception("Failed to load settings; running on defaults")


async def save_setting(key: str, value: Any) -> None:
    """Upsert one setting row (safe to fire-and-forget)."""
    db = await get_connection()
    try:
        async with _write_lock:
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
            await db.commit()
    except Exception:
        log.exception("Failed to save setting %r", key)


async def perform_factory_reset(state) -> None:
    """Restore defaults in state and wipe settings/ui_pages tables."""
    for key, value in config.SETTINGS_DEFAULTS.items():
        state.set_setting(key, value)

    state.custom_lcd_pages.clear()
    state.total_pages = config.BASE_PAGE_COUNT
    state.outdoor_temp = state.outdoor_humid = "N/A"
    state.outdoor_min = state.outdoor_max = "N/A"
    state.uv_current = state.uv_max = "N/A"
    state.weather_code = 0
    state.aqi_val = state.aqi_status = "N/A"
    state.page_changed = True

    db = await get_connection()
    try:
        async with _write_lock:
            await db.execute("DELETE FROM settings")
            await db.execute("DELETE FROM ui_pages")
            await db.commit()
    except Exception:
        log.exception("Factory reset DB wipe failed")


# ---------------------------------------------------------------------------
# Historical environmental logs
# ---------------------------------------------------------------------------

async def insert_weather_log(
    in_temp: Optional[float],
    in_humid: Optional[float],
    out_temp: Optional[float],
    out_humid: Optional[float],
) -> None:
    """Append one historical reading."""
    db = await get_connection()
    try:
        async with _write_lock:
            await db.execute(
                "INSERT INTO weather_logs (in_temp, in_humid, out_temp, out_humid) "
                "VALUES (?, ?, ?, ?)",
                (in_temp, in_humid, out_temp, out_humid),
            )
            await db.commit()
    except Exception:
        log.exception("Failed to insert weather log")


async def fetch_recent_logs(limit: int = 15) -> List[Sequence]:
    """Newest-first rows for dashboards."""
    db = await get_connection()
    try:
        async with db.execute(
            "SELECT timestamp, in_temp, in_humid, out_temp, out_humid "
            "FROM weather_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cursor:
            return list(await cursor.fetchall())
    except Exception:
        log.exception("Failed to fetch recent logs")
        return []


async def fetch_logs_page(limit: int = 100,
                          offset: int = 0) -> tuple:
    """Newest-first (rows, total_count) for the logs admin page."""
    db = await get_connection()
    try:
        async with db.execute("SELECT COUNT(*) FROM weather_logs") as cursor:
            total = (await cursor.fetchone())[0]
        async with db.execute(
            "SELECT id, timestamp, in_temp, in_humid, out_temp, out_humid "
            "FROM weather_logs ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cursor:
            return list(await cursor.fetchall()), total
    except Exception:
        log.exception("Failed to fetch log page")
        return [], 0


async def fetch_history_for_chart(limit: int = 200) -> List[Dict[str, Any]]:
    """Oldest-first rows for frontend trend charts."""
    db = await get_connection()
    try:
        async with db.execute(
            "SELECT timestamp, in_temp, out_temp, in_humid, out_humid "
            "FROM weather_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            {
                "timestamp": r[0],
                "in_temp": r[1],
                "out_temp": r[2],
                "in_humid": r[3],
                "out_humid": r[4],
            }
            for r in reversed(rows)
        ]
    except Exception:
        log.exception("Failed to fetch chart history")
        return []


async def export_all_logs_csv() -> str:
    """Full export as CSV text."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        ["ID", "Timestamp", "Indoor Temp (C)", "Indoor Humidity (%)",
         "Outdoor Temp (C)", "Outdoor Humidity (%)"]
    )
    db = await get_connection()
    try:
        async with db.execute(
            "SELECT id, timestamp, in_temp, in_humid, out_temp, out_humid "
            "FROM weather_logs ORDER BY id ASC"
        ) as cursor:
            async for row in cursor:
                writer.writerow(row)
    except Exception:
        log.exception("Failed to export logs")
    return out.getvalue()


async def export_all_logs_json() -> str:
    """Full log history as a JSON array of row objects."""
    db = await get_connection()
    rows: List[Dict[str, Any]] = []
    try:
        async with db.execute(
            "SELECT id, timestamp, in_temp, in_humid, out_temp, out_humid "
            "FROM weather_logs ORDER BY id ASC"
        ) as cursor:
            async for rid, ts, it, ih, ot, oh in cursor:
                rows.append({
                    "id": rid, "timestamp": ts,
                    "in_temp": it, "in_humid": ih,
                    "out_temp": ot, "out_humid": oh,
                })
    except Exception:
        log.exception("Failed to export logs as JSON")
    return json.dumps(rows, default=str)


async def export_all_data() -> Dict[str, Any]:
    """Everything in the DB: logs + settings + pages + page names.

    Powers the logs-page 'Export All' button (CSV + JSON bundle).
    """
    db = await get_connection()
    logs: List[Dict[str, Any]] = []
    settings: Dict[str, str] = {}
    ui_pages: Dict[str, str] = {}
    page_meta: Dict[str, str] = {}
    try:
        async with db.execute(
            "SELECT id, timestamp, in_temp, in_humid, out_temp, out_humid "
            "FROM weather_logs ORDER BY id ASC"
        ) as cursor:
            async for rid, ts, it, ih, ot, oh in cursor:
                logs.append({
                    "id": rid, "timestamp": ts,
                    "in_temp": it, "in_humid": ih,
                    "out_temp": ot, "out_humid": oh,
                })
        async with db.execute("SELECT key, value FROM settings") as cursor:
            async for key, value in cursor:
                settings[key] = value
        async with db.execute("SELECT page_id, layout_json FROM ui_pages") as cursor:
            async for pid, layout in cursor:
                ui_pages[str(pid)] = layout
        async with db.execute("SELECT page_id, name FROM page_meta") as cursor:
            async for pid, name in cursor:
                page_meta[str(pid)] = name
    except Exception:
        log.exception("Failed to export all data")
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "version": config.APP_VERSION,
        "record_count": len(logs),
        "weather_logs": logs,
        "settings": settings,
        "ui_pages": ui_pages,
        "page_meta": page_meta,
    }


async def export_all_data_csv() -> str:
    """Logs table CSV (same as export_all_logs_csv) — kept for the bundle
    endpoint so CSV and JSON exports always match."""
    return await export_all_logs_csv()


async def archive_old_logs() -> Dict[str, Any]:
    """ENH 3: gzip-archive weather_logs rows older than the cutoff.

    Rows older than LOG_ARCHIVE_AFTER_DAYS are written as one gzip-compressed
    JSON-lines file into logs_archive/, then deleted from the live table so
    the SQLite file stays small and fast (WAL keeps readers unblocked).
    """
    result: Dict[str, Any] = {"archived": 0, "archive_file": None,
                              "compress_logs": False}
    db = await get_connection()
    cutoff = (datetime.now(timezone.utc) - timedelta(
        days=config.LOG_ARCHIVE_AFTER_DAYS)).isoformat()
    try:
        async with db.execute(
            "SELECT id, timestamp, in_temp, in_humid, out_temp, out_humid "
            "FROM weather_logs WHERE timestamp < ? ORDER BY id ASC",
            (cutoff,),
        ) as cursor:
            rows = await cursor.fetchall()
        if not rows:
            return result

        config.LOGS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = config.LOGS_ARCHIVE_DIR / f"weather_logs_{stamp}.jsonl.gz"
        with gzip.open(archive_path, "wt", encoding="utf-8") as gz:
            for rid, ts, it, ih, ot, oh in rows:
                gz.write(json.dumps({
                    "id": rid, "timestamp": ts,
                    "in_temp": it, "in_humid": ih,
                    "out_temp": ot, "out_humid": oh,
                }) + "\n")

        ids = [r[0] for r in rows]
        async with _write_lock:
            await db.executemany(
                "DELETE FROM weather_logs WHERE id = ?",
                [(i,) for i in ids],
            )
            await db.commit()

        result.update({
            "archived": len(ids),
            "archive_file": archive_path.name,
            "compress_logs": True,
        })
        log.info("Archived %d log rows -> %s", len(ids), archive_path.name)
    except Exception:
        log.exception("Log archiving failed")
    return result


async def clear_all_logs() -> None:
    """Delete every historical row (admin action)."""
    db = await get_connection()
    try:
        async with _write_lock:
            await db.execute("DELETE FROM weather_logs")
            await db.commit()
    except Exception:
        log.exception("Failed to clear logs")


# ---------------------------------------------------------------------------
# Custom LCD page layouts
# ---------------------------------------------------------------------------

async def save_custom_page(page_id: int, widget_type: str) -> None:
    """Upsert one ui_pages row."""
    db = await get_connection()
    try:
        async with _write_lock:
            await db.execute(
                "INSERT INTO ui_pages (page_id, layout_json) VALUES (?, ?) "
                "ON CONFLICT(page_id) DO UPDATE SET layout_json=excluded.layout_json",
                (page_id, widget_type),
            )
            await db.commit()
    except Exception:
        log.exception("Failed to save page %s", page_id)


async def delete_custom_page(page_id: int) -> None:
    db = await get_connection()
    try:
        async with _write_lock:
            await db.execute("DELETE FROM ui_pages WHERE page_id = ?", (page_id,))
            await db.commit()
    except Exception:
        log.exception("Failed to delete page %s", page_id)


# ---------------------------------------------------------------------------
# Page tab names (designer customization)
# ---------------------------------------------------------------------------

async def rename_page(page_id: int, name: str) -> None:
    """Upsert a user-facing page tab name."""
    db = await get_connection()
    try:
        async with _write_lock:
            await db.execute(
                "INSERT INTO page_meta (page_id, name) VALUES (?, ?) "
                "ON CONFLICT(page_id) DO UPDATE SET name=excluded.name",
                (page_id, name),
            )
            await db.commit()
    except Exception:
        log.exception("Failed to rename page %s", page_id)


async def load_page_names(state) -> None:
    """Populate state.page_names from page_meta (falling back to defaults)."""
    db = await get_connection()
    try:
        async with db.execute("SELECT page_id, name FROM page_meta") as cursor:
            async for page_id, name in cursor:
                state.page_names[int(page_id)] = str(name)
    except Exception:
        log.exception("Failed to load page names")


# ---------------------------------------------------------------------------
# Runtime snapshot (graceful shutdown / restart continuity)
# ---------------------------------------------------------------------------

async def save_runtime_snapshot(state) -> None:
    """Persist page, settings, and page names ahead of a shutdown/restart."""
    try:
        await save_setting("current_page", state.current_page)
        for key in ("unit", "buzzer", "screen", "auto_scroll", "alarm_on",
                    "alarm_hr", "alarm_min", "api_rate", "log_rate",
                    "dht_offset_temp", "latitude", "longitude",
                    "voice_mode", "guest_mode", "screen_timeout",
                    "compress_logs", "alert_high", "alert_low"):
            await save_setting(key, state.get_setting(key))
        for page_id, name in state.page_names.items():
            await rename_page(page_id, name)
        for page_id, widget in state.custom_lcd_pages.items():
            await save_custom_page(page_id, widget)
        log.info("Runtime snapshot saved")
    except Exception:
        log.exception("Runtime snapshot failed")


async def load_runtime_snapshot(state) -> None:
    """Restore the persisted current_page after a restart."""
    db = await get_connection()
    try:
        async with db.execute(
            "SELECT value FROM settings WHERE key = 'current_page'"
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            page = int(row[0])
            if 1 <= page <= config.MAX_LCD_PAGES:
                state.current_page = page
    except Exception:
        log.exception("Runtime snapshot restore failed")
