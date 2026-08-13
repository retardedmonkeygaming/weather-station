# SkyCast Weather Station v3.0.0

**Your Environment, Understood**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Professional environmental monitoring system with LCD display, web dashboard, and Discord integration. Built for Raspberry Pi with full mock hardware support for PC development.

![SkyCast Weather Station](https://via.placeholder.com/800x400/0288d1/ffffff?text=SkyCast+Weather+Station+v3.0.0)

## Features

### 🖥️ LCD Display (16x2)
- **Page 0**: Clock + Date with animated colon and alarm indicator
- **Page 1**: Indoor Climate (`In:24.5C H:45%` + `Comfort! :)`)
- **Page 2**: Outdoor Weather (temperature + feels like)
- **Page 3**: Air Quality (`OK`, `Mod`, `Sens`, `Unhl`, `VUnh`, `Hazd`)
- **Page 4**: System Info (uptime, API fetch age, disk space)
- **Page 5**: Settings Menu (10 configurable items)

### 👆 Professional Touch Input
- Single tap → Next page
- Double tap → Previous page
- Triple tap → Enter/exit settings
- Short hold (0.8s) → Adjust setting value
- Medium hold (3s) → Factory reset
- Long hold (5s) → Reboot
- Extra long hold (10s) → Shutdown

### 🌐 Web Dashboard (Coming Soon)
- Live WebSocket updates
- Simulated LCD mirror
- Metric tiles with severity colors
- Settings management
- Historical charts
- Dark mode support

### 💬 Discord Bot (Coming Soon)
- First-join setup wizard
- Per-server and per-user configuration
- Natural language queries
- Proactive alerts and briefings
- Branded embeds with project colors

## Quick Start

### Installation on Raspberry Pi

```bash
# One-line installer (coming soon)
curl -sSL https://raw.githubusercontent.com/skycast/weather-station/main/scripts/install.sh | sudo bash

# Manual installation
git clone https://github.com/skycast/weather-station.git
cd weather-station
pip install -e .
skycast
```

### Running Without Hardware (PC Development)

```bash
# Install with mock profile
pip install -e ".[dev]"
export SKYCAST_PROFILE=mock
python -m src.weather_station.main
```

## Configuration

Create a `.env` file in the project root:

```env
# Application
SKYCAST_PROFILE=production

# Location
LOCATION_LATITUDE=40.7128
LOCATION_LONGITUDE=-74.0060
LOCATION_TIMEZONE=America/New_York

# Sensors
SENSOR_MOCK_HARDWARE=false
SENSOR_I2C_BUS=1
SENSOR_LCD_ADDRESS=0x27

# Alerts
ALERT_TEMP_HIGH=30.0
ALERT_TEMP_LOW=5.0
ALERT_BUZZER_MODE=ALERTS
ALERT_QUIET_HOURS_START=22
ALERT_QUIET_HOURS_END=7

# Discord (optional)
DISCORD_TOKEN=your_bot_token_here
DISCORD_ENABLED=false

# Web Server
WEB_HOST=0.0.0.0
WEB_PORT=8000
```

## Project Structure

```
src/weather_station/
├── __init__.py          # Package metadata, branding
├── main.py              # Application factory
├── core/
│   ├── config.py        # Pydantic settings
│   ├── state.py         # Central AppState
│   └── events.py        # EventBus for decoupled communication
├── hardware/
│   └── interfaces.py    # HAL with MockHardware + RealHardware
├── persistence/
│   ├── models.py        # SQLAlchemy models (7 tables)
│   └── database.py      # DatabaseManager with repository pattern
├── input/
│   └── processor.py     # Touch gesture recognition
├── display/
│   ├── manager.py       # DisplayManager
│   └── widgets.py       # 6 LCD widgets
├── services/
│   ├── weather.py       # WeatherService with retry logic
│   └── system.py        # SystemService (alerts, shutdown)
└── web/                 # (Coming soon)
    └── discord/         # (Coming soon)
```

## Architecture

SkyCast uses a clean modular architecture:

1. **AppState**: Single source of truth for all system state
2. **EventBus**: Decoupled pub/sub communication between components
3. **Hardware Abstraction**: Interfaces with mock implementation for PC development
4. **Repository Pattern**: Thin data-access layer over SQLAlchemy
5. **Application Factory**: Clean initialization and lifecycle management

## Settings Menu

The 16x2 LCD displays these 10 settings:

| # | Setting | Values |
|---|---------|--------|
| 0 | Temp Unit | C / F |
| 1 | Buzzer Mode | ALL / ALERTS / MUTE |
| 2 | Screen Power | ON / OFF |
| 3 | Auto Scroll | ON / OFF |
| 4 | Daily Alarm | OFF / ON |
| 5 | Alert Temp Hi | -10 to 50°C |
| 6 | Alert Temp Lo | -10 to 50°C |
| 7 | Sensor Offset | -5.0 to +5.0 |
| 8 | Quiet Hours | 22-7 (configurable) |
| 9 | Factory Reset | NO / YES |

## Database Schema

7 tables with provenance tracking:

- `settings` - All configuration with last-changed-by metadata
- `sensor_logs` - Historical sensor readings (auto-retention)
- `alert_logs` - Alert history for auditing
- `discord_server_configs` - Per-server Discord settings
- `discord_user_configs` - Per-user preferences
- `update_checks` - GitHub update check results
- `system_events` - Audit log for system events

## Roadmap

### Phase 1: Core Foundation ✅
- [x] Modular package structure
- [x] AppState + EventBus
- [x] Hardware abstraction layer
- [x] Database with repository pattern
- [x] Professional touch input
- [x] LCD widgets (6 pages)
- [x] Weather + System services

### Phase 2: Web Dashboard (Next)
- [ ] FastAPI with Jinja2 templates
- [ ] WebSocket live updates
- [ ] Settings UI with instant sync
- [ ] Historical charts
- [ ] Dark mode

### Phase 3: Discord Integration
- [ ] Setup wizard on server join
- [ ] Per-server/per-user configs
- [ ] Natural language queries
- [ ] Proactive alerts

### Phase 4: Polish & Distribution
- [ ] Update checker (GitHub Releases)
- [ ] Health endpoints
- [ ] Raspberry Pi installer script
- [ ] Docker Compose (optional)
- [ ] Documentation site

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
black src/

# Type checking
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

Built with ❤️ by the SkyCast Team
