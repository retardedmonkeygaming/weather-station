"""Database initialization and persistence operations."""
import aiosqlite
from typing import Dict, Any

DB_FILE = "weather_history.db"


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
        await db.commit()


async def save_setting(key: str, value: str, db_path: str = DB_FILE):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        await db.commit()


async def load_settings(db_path: str = DB_FILE) -> Dict[str, str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT key, value FROM settings") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


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
                data.get("aqi")
            )
        )
        await db.commit()