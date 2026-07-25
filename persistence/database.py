"""Database initialization, settings persistence, and custom layouts."""
import aiosqlite
from typing import Dict, Any

DB_FILE = "weather_history.db"

DEFAULT_SETTINGS = {
    "temp_unit": "C",
    "buzzer_mode": "ALL",
    "backlight_enabled": "True",
    "auto_scroll_speed": "3",
    "alarm_time": "07:00",
    "alarm_enabled": "False",
    "log_interval": "300",
    "api_fetch_interval": "600",
    "temp_offset": "0.0",
    "humid_offset": "0.0",
    "night_mode": "False",
    "high_temp_threshold": "35.0",
    "low_temp_threshold": "5.0",
    "webhook_url": "",
    "enabled_pages": "1,2,3,4,5,6,7"
    ,
    # default mapping: page slot -> widget id
    "page_widget_map": "{\"1\":1, \"2\":2, \"3\":3, \"4\":4, \"5\":5, \"6\":6, \"7\":7}"
}


async def init_db(db_path: str = DB_FILE):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sensor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                indoor_temp REAL,
                indoor_humid REAL,
                outdoor_temp REAL,
                outdoor_humid REAL,
                uv_index REAL,
                aqi INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_pages (
                page_id INTEGER PRIMARY KEY,
                widget_type TEXT
            )
        """)
        
        for key, val in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, val)
            )
        await db.commit()


async def save_setting(key: str, value: Any, db_path: str = DB_FILE):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        await db.commit()


async def load_all_settings(db_path: str = DB_FILE) -> Dict[str, str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT key, value FROM settings") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


async def factory_reset_db(db_path: str = DB_FILE):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM settings")
        for key, val in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                (key, val)
            )
        await db.commit()


async def log_sensor_data(data: Dict[str, Any], db_path: str = DB_FILE):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO sensor_logs 
               (indoor_temp, indoor_humid, outdoor_temp, outdoor_humid, uv_index, aqi) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data.get("indoor_temp"),
                data.get("indoor_humid"),
                data.get("outdoor_temp"),
                data.get("outdoor_humid"),
                data.get("uv_current"),
                data.get("aqi_val") if data.get("aqi_val") != "N/A" else None
            )
        )
        await db.commit()