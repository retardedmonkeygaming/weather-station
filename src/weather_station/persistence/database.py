import aiosqlite
import logging
from weather_station.persistence.models import SCHEMA
from weather_station.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_path = settings.db_file

    async def initialize(self):
        """Creates tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            for table_name, query in SCHEMA.items():
                await db.execute(query)
            await db.commit()
            logger.info("Database initialized successfully.")

    async def log_weather(self, in_t, in_h, out_t, out_h):
        """Saves a weather snapshot."""
        query = "INSERT INTO weather_logs (in_temp, in_humid, out_temp, out_humid) VALUES (?, ?, ?, ?)"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, (in_t, in_h, out_t, out_h))
            await db.commit()

    async def save_setting(self, key: str, value: str):
        query = "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, (key, value))
            await db.commit()

    async def load_settings(self) -> dict:
        """Returns all stored settings as a dictionary."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT key, value FROM settings") as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}

    async def get_ui_pages(self) -> dict:
        """Loads the custom LCD layouts designed in the Web UI."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT page_id, widget_type FROM ui_pages") as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}
    
    async def save_page_assignment(self, page_id: int, widget_type: str):
        """Saves a custom LCD page layout to the DB."""
        query = "INSERT OR REPLACE INTO ui_pages (page_id, widget_type) VALUES (?, ?)"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, (page_id, widget_type))
            await db.commit()

    async def save_setting(self, key: str, value: str):
        """Saves a system setting (Unit, API Rate, etc) to the DB."""
        query = "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, (key, value))
            await db.commit()