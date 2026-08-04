import aiosqlite
from weather_station.core.config import settings

class DatabaseManager:
    def __init__(self):
        self.db_path = settings.db_file

    def get_connection(self):
        return aiosqlite.connect(self.db_path)

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS weather_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT DEFAULT CURRENT_TIMESTAMP, in_temp REAL, in_humid REAL, out_temp REAL, out_humid REAL)")
            await db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            await db.execute("CREATE TABLE IF NOT EXISTS ui_pages (page_id INTEGER PRIMARY KEY, widget_type TEXT)")
            await db.commit()

    async def save_page_assignment(self, page_id: int, widget_type: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO ui_pages (page_id, widget_type) VALUES (?, ?)", (page_id, widget_type))
            await db.commit()

    async def save_setting(self, key: str, value: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            await db.commit()