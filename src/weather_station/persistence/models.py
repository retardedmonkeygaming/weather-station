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
            value TEXT
        )
    """,
    "ui_pages": """
        CREATE TABLE IF NOT EXISTS ui_pages (
            page_id INTEGER PRIMARY KEY,
            widget_type TEXT
        )
    """
}