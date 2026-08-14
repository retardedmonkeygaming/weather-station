# Weather Station System

A professional, multi-surface weather station system for Raspberry Pi with LCD display, web dashboard, and Discord bot integration.

## Phase 2: Core Architecture Complete

This phase establishes the foundational architecture including:

- **Modular Package Structure**: Clean separation of concerns across core, hardware, database, config, and utils modules
- **AppState**: Centralized state management for all sensor data, system status, and configuration
- **EventSystem**: Pub/sub event bus for cross-component communication
- **SettingsManager**: Persistent configuration with validation, tracking, and import/export
- **DatabaseManager**: Async SQLite operations for settings, logs, UI pages, and Discord data
- **Hardware Abstraction**: Mock and real implementations for DHT sensor, button, buzzer, and LCD
- **Utility Functions**: Moon phase calculation, temperature formatting, comfort levels, and more

## Project Structure

```
weather_station/
├── __init__.py          # Package exports
├── main.py              # Main entry point
├── core/
│   ├── __init__.py
│   ├── app_state.py     # AppState and data containers
│   └── events.py        # EventSystem and EventType
├── config/
│   ├── __init__.py
│   └── settings.py      # SettingsManager and SettingDefinition
├── db/
│   ├── __init__.py
│   └── database.py      # DatabaseManager
├── hardware/
│   ├── __init__.py
│   └── drivers.py       # Mock and real hardware drivers
└── utils/
    ├── __init__.py
    └── helpers.py       # Utility functions
```

## Installation

```bash
pip install aiosqlite aiohttp
```

For full hardware support on Raspberry Pi:
```bash
pip install gpiozero adafruit-blinka adafruit-circuitpython-character-lcd adafruit-circuitpython-dht
```

## Usage

### Run with Mock Hardware (Development)
```bash
python -m weather_station.main --mock
```

### Run with Real Hardware (Production)
```bash
python -m weather_station.main
```

## Features

### Core State Management
- Single `AppState` object holds all live data
- Type-safe data containers for sensors, system info, alerts, etc.
- Automatic moon phase calculation

### Persistent Settings
- All settings stored in SQLite database
- Validation with min/max constraints and option lists
- Change tracking (who changed what and when)
- JSON import/export for backups
- Grouped settings (Display, Audio, Alerts, Data, Location, Discord)

### Event System
- Publish/subscribe pattern for loose coupling
- Event types for sensor updates, alerts, settings changes, etc.
- Async callback support

### Hardware Abstraction
- Mock hardware for development without physical components
- Seamless switch between mock and real hardware
- Simulated sensor errors for testing

### Database Layer
- Async SQLite operations with aiosqlite
- Tables for settings, weather logs, UI pages, Discord guilds/users
- Automatic schema creation and indexing

## Configuration

Default settings are defined in `SettingsManager` and include:

| Setting | Default | Description |
|---------|---------|-------------|
| unit | C | Temperature unit (C/F) |
| temp_offset | 0.0 | Sensor calibration offset |
| temp_high_threshold | 32.0 | High temp alert threshold |
| temp_low_threshold | 10.0 | Low temp alert threshold |
| buzzer_mode | ALL | Buzzer mode (ALL/ERR/MUTE) |
| screen_on | True | Display power |
| auto_scroll_interval | 0 | Page rotation interval (0=off) |
| alarm_enabled | False | Daily alarm |
| api_fetch_interval | 10 | Weather API fetch rate (min) |
| log_interval | 15 | Database logging rate (min) |

## Next Phases

- **Phase 3**: Web UI with Jinja2 templates, WebSocket live updates, professional design
- **Phase 4**: Discord bot with slash commands, natural language processing, per-server settings
- **Phase 5**: Update checker, health endpoints, packaging, documentation

## License

MIT License
