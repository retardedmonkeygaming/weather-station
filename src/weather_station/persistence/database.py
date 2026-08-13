import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
from weather_station.core.config import settings
from weather_station.persistence.models import SCHEMA


class DatabaseManager:
    """Centralized database manager for all persistence operations."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.db_file

    async def initialize(self) -> None:
        """Initialize database with all required tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Create all tables from schema
            for table_name, create_sql in SCHEMA.items():
                await db.execute(create_sql)
            
            # Initialize default settings if not present
            await self._init_default_settings(db)
            await db.commit()

    async def _init_default_settings(self, db: aiosqlite.Connection) -> None:
        """Insert default settings if they don't exist."""
        defaults = [
            ("unit", "C", "system"),
            ("buzzer_mode", "ALL", "system"),
            ("api_rate", str(settings.api_rate), "system"),
            ("log_rate", str(settings.log_rate), "system"),
            ("alert_enabled", "False", "system"),
            ("alert_hour", str(settings.alert_hour), "system"),
            ("alert_minute", str(settings.alert_minute), "system"),
            ("theme", "auto", "system"),
            ("idle_timeout", str(settings.idle_timeout), "system"),
        ]
        
        for key, value, modified_by in defaults:
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value, modified_by) VALUES (?, ?, ?)",
                (key, value, modified_by)
            )

    async def get_logs(self, limit: int = 15) -> List[tuple]:
        """Fetch recent weather logs."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                f"SELECT timestamp, in_temp, in_humid, out_temp, out_humid FROM weather_logs ORDER BY id DESC LIMIT {limit}"
            ) as cursor:
                return await cursor.fetchall()

    async def get_total_logs(self) -> int:
        """Get total count of weather logs."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM weather_logs") as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0

    async def save_weather_log(
        self, 
        in_temp: float, 
        in_humid: float, 
        out_temp: float, 
        out_humid: float
    ) -> None:
        """Save a new weather log entry."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO weather_logs (in_temp, in_humid, out_temp, out_humid) VALUES (?, ?, ?, ?)",
                (in_temp, in_humid, out_temp, out_humid)
            )
            await db.commit()

    async def save_page_assignment(self, page_id: int, widget_type: str) -> None:
        """Save UI page widget assignment."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO ui_pages (page_id, widget_type) VALUES (?, ?)",
                (page_id, widget_type)
            )
            await db.commit()

    async def delete_page_assignment(self, page_id: int) -> None:
        """Delete UI page widget assignment."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM ui_pages WHERE page_id = ?", (page_id,))
            await db.commit()
            
    async def save_setting(
        self, 
        key: str, 
        value: str, 
        modified_by: str = "web"
    ) -> None:
        """Save a setting with tracking of who modified it."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value, modified_by, modified_at) VALUES (?, ?, ?, ?)",
                (key, value, modified_by, datetime.now().isoformat())
            )
            await db.commit()

    async def get_setting(self, key: str, default: str = "") -> str:
        """Get a single setting value."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default

    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT key, value, modified_by, modified_at FROM settings") as cursor:
                rows = await cursor.fetchall()
                return {
                    row[0]: {
                        "value": row[1],
                        "modified_by": row[2],
                        "modified_at": row[3]
                    }
                    for row in rows
                }

    async def save_discord_server(
        self,
        server_id: str,
        channel_id: Optional[str] = None,
        allowed_roles: Optional[str] = None,
        nl_enabled: bool = True,
        briefing_hour: int = 7,
        quiet_hours_start: int = 22,
        quiet_hours_end: int = 7
    ) -> None:
        """Save Discord server configuration."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO discord_servers 
                   (server_id, channel_id, allowed_roles, nl_enabled, briefing_hour, quiet_hours_start, quiet_hours_end)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (server_id, channel_id, allowed_roles, nl_enabled, briefing_hour, quiet_hours_start, quiet_hours_end)
            )
            await db.commit()

    async def get_discord_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get Discord server configuration."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM discord_servers WHERE server_id = ?", (server_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def save_discord_user(
        self,
        user_id: str,
        preferred_units: str = "C",
        dm_briefing_enabled: bool = False,
        custom_thresholds: Optional[str] = None
    ) -> None:
        """Save Discord user preferences."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO discord_users 
                   (user_id, preferred_units, dm_briefing_enabled, custom_thresholds)
                   VALUES (?, ?, ?, ?)""",
                (user_id, preferred_units, dm_briefing_enabled, custom_thresholds)
            )
            await db.commit()

    async def get_discord_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get Discord user preferences."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM discord_users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def log_system_event(self, event_type: str, event_data: str) -> None:
        """Log a system event for diagnostics."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO system_events (event_type, event_data) VALUES (?, ?)",
                (event_type, event_data)
            )
            await db.commit()

    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent system events."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM system_events ORDER BY timestamp DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def save_update_check(
        self,
        current_version: str,
        latest_version: str,
        release_notes: Optional[str] = None,
        update_available: bool = False
    ) -> None:
        """Save GitHub update check result."""
        async with aiosqlite.connect(self.db_path) as db:
            # Clear old entries
            await db.execute("DELETE FROM update_checks")
            await db.execute(
                """INSERT INTO update_checks 
                   (last_check, current_version, latest_version, release_notes, update_available)
                   VALUES (?, ?, ?, ?, ?)""",
                (datetime.now().isoformat(), current_version, latest_version, release_notes, update_available)
            )
            await db.commit()

    async def get_update_status(self) -> Optional[Dict[str, Any]]:
        """Get the latest update check status."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM update_checks ORDER BY id DESC LIMIT 1") as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def vacuum(self) -> None:
        """Vacuum database to optimize storage."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("VACUUM")
            await db.commit()

    async def export_config(self) -> Dict[str, Any]:
        """Export all configuration as JSON-serializable dict."""
        settings_data = await self.get_all_settings()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get page assignments
            async with db.execute("SELECT * FROM ui_pages") as cursor:
                pages = [dict(row) for row in await cursor.fetchall()]
            
            # Get Discord servers
            async with db.execute("SELECT * FROM discord_servers") as cursor:
                servers = [dict(row) for row in await cursor.fetchall()]
            
            # Get Discord users
            async with db.execute("SELECT * FROM discord_users") as cursor:
                users = [dict(row) for row in await cursor.fetchall()]
        
        return {
            "settings": settings_data,
            "ui_pages": pages,
            "discord_servers": servers,
            "discord_users": users,
            "exported_at": datetime.now().isoformat()
        }

    async def import_config(self, config: Dict[str, Any]) -> None:
        """Import configuration from exported dict."""
        async with aiosqlite.connect(self.db_path) as db:
            # Import settings
            for key, data in config.get("settings", {}).items():
                value = data.get("value", "") if isinstance(data, dict) else data
                await db.execute(
                    "INSERT OR REPLACE INTO settings (key, value, modified_by, modified_at) VALUES (?, ?, ?, ?)",
                    (key, value, "import", datetime.now().isoformat())
                )
            
            # Import UI pages
            for page in config.get("ui_pages", []):
                await db.execute(
                    "INSERT OR REPLACE INTO ui_pages (page_id, widget_type) VALUES (?, ?)",
                    (page.get("page_id"), page.get("widget_type"))
                )
            
            await db.commit()