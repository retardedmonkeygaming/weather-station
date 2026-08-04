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

        async def initialize(self):
                async with aiosqlite.connect(self.db_path) as db:
                    # Weather Logs (Existing)
                    await db.execute("CREATE TABLE IF NOT EXISTS weather_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, in_temp REAL, in_humid REAL, out_temp REAL, out_humid REAL)")
                    
                    # LYRICPULSE: Songs Table
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS songs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL, artist TEXT NOT NULL,
                            play_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # LYRICPULSE: Lyrics Table
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS song_lyrics (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, song_id INTEGER,
                            timestamp_sec REAL NOT NULL, line1 TEXT, line2 TEXT,
                            FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                        )
                    """)
                    await db.commit()

        async def get_all_songs(self):
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute("SELECT * FROM songs ORDER BY title ASC") as cursor:
                        rows = await cursor.fetchall()
                        return [dict(r) for r in rows]

        async def get_song_lyrics(self, song_id: int):
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute("SELECT timestamp_sec, line1, line2 FROM song_lyrics WHERE song_id = ? ORDER BY timestamp_sec ASC", (song_id,)) as cursor:
                        return await cursor.fetchall()