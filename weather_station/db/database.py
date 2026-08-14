"""
Database Management System
Handles SQLite database operations with async support.
"""

import aiosqlite
from datetime import datetime
from typing import Optional, List, Tuple, Any
from pathlib import Path


class DatabaseManager:
    """
    Async SQLite database manager for weather station data.
    Handles connections, migrations, and CRUD operations.
    """
    
    def __init__(self, db_path: str = "/home/admin/weather_station.db"):
        self.db_path = Path(db_path)
        self._connection: Optional[aiosqlite.Connection] = None
        self._initialized = False
    
    async def connect(self) -> None:
        """Establish database connection"""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row
        await self.execute("PRAGMA journal_mode=WAL")
        await self.execute("PRAGMA foreign_keys=ON")
    
    async def close(self) -> None:
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def ensure_tables(self) -> None:
        """Create all required tables if they don't exist"""
        if self._initialized:
            return
        
        # Settings table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                changed_by TEXT DEFAULT 'system',
                changed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Weather logs table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS weather_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                in_temp REAL,
                in_humid REAL,
                out_temp REAL,
                out_humid REAL,
                aqi INTEGER,
                pm2_5 REAL,
                pm10 REAL
            )
        """)
        
        # UI pages table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS ui_pages (
                page_id INTEGER PRIMARY KEY,
                layout_json TEXT NOT NULL
            )
        """)
        
        # Discord guilds table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS discord_guilds (
                guild_id TEXT PRIMARY KEY,
                name TEXT,
                alert_channel_id TEXT,
                allowed_role_ids TEXT,
                natural_language_enabled INTEGER DEFAULT 1,
                briefing_hour INTEGER DEFAULT 8,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Discord users table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS discord_users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                preferred_units TEXT DEFAULT 'C',
                dm_alerts_enabled INTEGER DEFAULT 1,
                temp_high_threshold REAL,
                temp_low_threshold REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # System events log table
        await self.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                source TEXT,
                details TEXT
            )
        """)
        
        # Create indexes for performance
        await self.execute("CREATE INDEX IF NOT EXISTS idx_weather_logs_timestamp ON weather_logs(timestamp)")
        await self.execute("CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events(timestamp)")
        await self.execute("CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type)")
        
        self._initialized = True
    
    async def execute(self, query: str, parameters: tuple = ()) -> int:
        """Execute a write query and return rows affected"""
        if not self._connection:
            raise RuntimeError("Database not connected")
        
        cursor = await self._connection.execute(query, parameters)
        await self._connection.commit()
        return cursor.rowcount
    
    async def fetch_one(self, query: str, parameters: tuple = ()) -> Optional[Tuple]:
        """Fetch a single row"""
        if not self._connection:
            raise RuntimeError("Database not connected")
        
        cursor = await self._connection.execute(query, parameters)
        row = await cursor.fetchone()
        return tuple(row) if row else None
    
    async def fetch_all(self, query: str, parameters: tuple = ()) -> List[Tuple]:
        """Fetch all rows"""
        if not self._connection:
            raise RuntimeError("Database not connected")
        
        cursor = await self._connection.execute(query, parameters)
        rows = await cursor.fetchall()
        return [tuple(row) for row in rows]
    
    async def log_weather(self, in_temp: float, in_humid: float, 
                         out_temp: Optional[float] = None, 
                         out_humid: Optional[float] = None,
                         aqi: Optional[int] = None,
                         pm2_5: Optional[float] = None,
                         pm10: Optional[float] = None) -> int:
        """Insert a weather log entry"""
        await self.execute("""
            INSERT INTO weather_logs (in_temp, in_humid, out_temp, out_humid, aqi, pm2_5, pm10)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (in_temp, in_humid, out_temp, out_humid, aqi, pm2_5, pm10))
        
        # Get last inserted ID
        cursor = await self._connection.execute("SELECT last_insert_rowid()")
        row = await cursor.fetchone()
        return row[0] if row else 0
    
    async def log_event(self, event_type: str, source: str = "system", 
                       details: Optional[str] = None) -> int:
        """Log a system event"""
        await self.execute("""
            INSERT INTO system_events (event_type, source, details)
            VALUES (?, ?, ?)
        """, (event_type, source, details))
        
        cursor = await self._connection.execute("SELECT last_insert_rowid()")
        row = await cursor.fetchone()
        return row[0] if row else 0
    
    async def get_recent_logs(self, limit: int = 100) -> List[Tuple]:
        """Get recent weather logs"""
        return await self.fetch_all(
            "SELECT id, timestamp, in_temp, in_humid, out_temp, out_humid, aqi, pm2_5, pm10 "
            "FROM weather_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        )
    
    async def clear_logs(self) -> int:
        """Delete all weather logs"""
        return await self.execute("DELETE FROM weather_logs")
    
    async def get_log_count(self) -> int:
        """Get total number of log entries"""
        result = await self.fetch_one("SELECT COUNT(*) FROM weather_logs")
        return result[0] if result else 0
    
    async def save_ui_page(self, page_id: int, layout_json: str) -> None:
        """Save a custom UI page configuration"""
        await self.execute("""
            INSERT INTO ui_pages (page_id, layout_json)
            VALUES (?, ?)
            ON CONFLICT(page_id) DO UPDATE SET layout_json=excluded.layout_json
        """, (page_id, layout_json))
    
    async def load_ui_pages(self) -> dict:
        """Load all custom UI pages"""
        rows = await self.fetch_all("SELECT page_id, layout_json FROM ui_pages")
        return {row[0]: row[1] for row in rows}
    
    async def delete_ui_page(self, page_id: int) -> None:
        """Delete a custom UI page"""
        await self.execute("DELETE FROM ui_pages WHERE page_id = ?", (page_id,))
    
    async def save_guild(self, guild_id: str, name: str, 
                        alert_channel_id: Optional[str] = None,
                        allowed_role_ids: Optional[str] = None,
                        natural_language_enabled: bool = True,
                        briefing_hour: int = 8) -> None:
        """Save Discord guild settings"""
        await self.execute("""
            INSERT INTO discord_guilds (guild_id, name, alert_channel_id, allowed_role_ids, 
                                       natural_language_enabled, briefing_hour, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                name=excluded.name,
                alert_channel_id=excluded.alert_channel_id,
                allowed_role_ids=excluded.allowed_role_ids,
                natural_language_enabled=excluded.natural_language_enabled,
                briefing_hour=excluded.briefing_hour,
                updated_at=excluded.updated_at
        """, (guild_id, name, alert_channel_id, allowed_role_ids, 
              1 if natural_language_enabled else 0, briefing_hour, datetime.now().isoformat()))
    
    async def load_guild(self, guild_id: str) -> Optional[dict]:
        """Load Discord guild settings"""
        row = await self.fetch_one(
            "SELECT * FROM discord_guilds WHERE guild_id = ?",
            (guild_id,)
        )
        if row:
            return {
                "guild_id": row[0],
                "name": row[1],
                "alert_channel_id": row[2],
                "allowed_role_ids": row[3],
                "natural_language_enabled": bool(row[4]),
                "briefing_hour": row[5],
                "created_at": row[6],
                "updated_at": row[7]
            }
        return None
    
    async def save_user(self, user_id: str, username: str,
                       preferred_units: str = "C",
                       dm_alerts_enabled: bool = True,
                       temp_high_threshold: Optional[float] = None,
                       temp_low_threshold: Optional[float] = None) -> None:
        """Save Discord user settings"""
        await self.execute("""
            INSERT INTO discord_users (user_id, username, preferred_units, dm_alerts_enabled,
                                      temp_high_threshold, temp_low_threshold, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                preferred_units=excluded.preferred_units,
                dm_alerts_enabled=excluded.dm_alerts_enabled,
                temp_high_threshold=excluded.temp_high_threshold,
                temp_low_threshold=excluded.temp_low_threshold,
                updated_at=excluded.updated_at
        """, (user_id, username, preferred_units, 1 if dm_alerts_enabled else 0,
              temp_high_threshold, temp_low_threshold, datetime.now().isoformat()))
    
    async def load_user(self, user_id: str) -> Optional[dict]:
        """Load Discord user settings"""
        row = await self.fetch_one(
            "SELECT * FROM discord_users WHERE user_id = ?",
            (user_id,)
        )
        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "preferred_units": row[2],
                "dm_alerts_enabled": bool(row[3]),
                "temp_high_threshold": row[4],
                "temp_low_threshold": row[5],
                "created_at": row[6],
                "updated_at": row[7]
            }
        return None
    
    async def export_to_dict(self) -> dict:
        """Export all database content as a dictionary"""
        return {
            "settings": await self.fetch_all("SELECT * FROM settings"),
            "weather_logs": await self.fetch_all("SELECT * FROM weather_logs"),
            "ui_pages": await self.fetch_all("SELECT * FROM ui_pages"),
            "discord_guilds": await self.fetch_all("SELECT * FROM discord_guilds"),
            "discord_users": await self.fetch_all("SELECT * FROM discord_users"),
            "system_events": await self.fetch_all("SELECT * FROM system_events ORDER BY id DESC LIMIT 1000")
        }
