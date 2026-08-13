SCHEMA = {
    "weather_logs": """
        CREATE TABLE IF NOT EXISTS weather_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            in_temp REAL,
            in_humid REAL,
            out_temp REAL,
            out_humid REAL
        )
    """,
    "settings": """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            modified_by TEXT DEFAULT 'system',
            modified_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "ui_pages": """
        CREATE TABLE IF NOT EXISTS ui_pages (
            page_id INTEGER PRIMARY KEY,
            widget_type TEXT
        )
    """,
    "discord_servers": """
        CREATE TABLE IF NOT EXISTS discord_servers (
            server_id TEXT PRIMARY KEY,
            channel_id TEXT,
            allowed_roles TEXT,
            nl_enabled INTEGER DEFAULT 1,
            briefing_hour INTEGER DEFAULT 7,
            quiet_hours_start INTEGER DEFAULT 22,
            quiet_hours_end INTEGER DEFAULT 7,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "discord_users": """
        CREATE TABLE IF NOT EXISTS discord_users (
            user_id TEXT PRIMARY KEY,
            preferred_units TEXT DEFAULT 'C',
            dm_briefing_enabled INTEGER DEFAULT 0,
            custom_thresholds TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "system_events": """
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            event_data TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "update_checks": """
        CREATE TABLE IF NOT EXISTS update_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_check DATETIME,
            current_version TEXT,
            latest_version TEXT,
            release_notes TEXT,
            update_available INTEGER DEFAULT 0
        )
    """
}