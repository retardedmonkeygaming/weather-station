import aiosqlite
from weather_station.core.config import settings

class DatabaseManager:
    def __init__(self):
        self.db_path = settings.db_file

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS weather_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, in_temp REAL, in_humid REAL, out_temp REAL, out_humid REAL)")
            await db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            await db.execute("CREATE TABLE IF NOT EXISTS ui_pages (page_id INTEGER PRIMARY KEY, widget_type TEXT)")
            await db.commit()

    async def get_logs(self, limit=15):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f"SELECT timestamp, in_temp, in_humid, out_temp, out_humid FROM weather_logs ORDER BY id DESC LIMIT {limit}") as cursor:
                return await cursor.fetchall()

    async def get_total_logs(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM weather_logs") as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0

    async def save_page_assignment(self, page_id: int, widget_type: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO ui_pages (page_id, widget_type) VALUES (?, ?)", (page_id, widget_type))
            await db.commit()

    async def delete_page_assignment(self, page_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM ui_pages WHERE page_id = ?", (page_id,))
            await db.commit()
            
    async def save_setting(self, key: str, value: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            await db.commit()