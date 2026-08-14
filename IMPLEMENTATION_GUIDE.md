# SkyCast Weather Station - Professional Implementation Guide

## Overview

This document provides detailed guidance for implementing the complete professional recommendation set for the SkyCast Weather Station project. The recommendations transform the system from a functional prototype into a polished, production-ready product with consistent identity across all surfaces.

---

## 1. Overall System Identity & Consistency

### Visual Language
- **Primary Blue**: `#0288d1` (Material Design Blue 700)
- **LCD Green**: `#33ff33` (simulated phosphor green)
- **Neutral Greys**: `#263238` (text), `#546e7a` (secondary), `#cfd8dc` (borders)
- **Status Colors**:
  - Green (`#2e7d32`) = healthy/comfort
  - Amber (`#f57c00`) = caution/warning  
  - Red (`#c62828`) = alert/error

### Branding Elements
- **Official Name**: "SkyCast Weather Station"
- **Tagline**: "Your window to the weather — indoors and out"
- **Version**: `3.0.0`

### Implementation Status
✅ **COMPLETED** - Added to `/workspace/src/weather_station/__init__.py`:
```python
VERSION = "3.0.0"
PROJECT_NAME = "SkyCast Weather Station"
TAGLINE = "Your window to the weather — indoors and out"
```

### Next Steps
- Apply branding to LCD boot splash
- Add to web footer
- Include in Discord `/about` embed
- Display in README header

---

## 2. Modular Architecture

### Package Structure
```
src/weather_station/
├── __init__.py          # Version, project metadata
├── main.py              # Entry point with console script
├── core/
│   ├── state.py         # AppState singleton
│   └── config.py        # Pydantic settings
├── persistence/
│   ├── models.py        # Database schema
│   └── database.py      # DatabaseManager class
├── hardware/            # Hardware drivers (mockable)
├── services/            # Business logic
├── display/             # LCD management
├── input/               # Button handling
└── web/                 # FastAPI application
```

### Key Patterns
- Single `AppState` object shared across all modules
- All background tasks read/write to central state + SQLite
- Hardware drivers behind narrow interfaces for mocking
- Configuration via Pydantic with YAML/TOML + env vars
- Settings changes emit internal events for sync

### Implementation Status
✅ **COMPLETED** - Core architecture files updated:
- `state.py`: Added `settings_last_modified`, `discord_ready`, `discord_guilds`
- `config.py`: Full Pydantic validation with field descriptions
- `database.py`: Comprehensive DatabaseManager with 20+ methods
- `main.py`: Clean entry point with `main_entry()` console script

---

## 3. Persistent Settings & Expanded Menu

### Database Schema Extensions
✅ **COMPLETED** - New tables in `models.py`:
```sql
-- Settings with provenance tracking
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    modified_by TEXT DEFAULT 'system',
    modified_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Discord per-server configuration
CREATE TABLE discord_servers (
    server_id TEXT PRIMARY KEY,
    channel_id TEXT,
    allowed_roles TEXT,
    nl_enabled INTEGER DEFAULT 1,
    briefing_hour INTEGER DEFAULT 7,
    quiet_hours_start INTEGER DEFAULT 22,
    quiet_hours_end INTEGER DEFAULT 7
);

-- Discord per-user preferences
CREATE TABLE discord_users (
    user_id TEXT PRIMARY KEY,
    preferred_units TEXT DEFAULT 'C',
    dm_briefing_enabled INTEGER DEFAULT 0,
    custom_thresholds TEXT
);

-- Update checking
CREATE TABLE update_checks (
    last_check DATETIME,
    current_version TEXT,
    latest_version TEXT,
    release_notes TEXT,
    update_available INTEGER DEFAULT 0
);

-- System events for diagnostics
CREATE TABLE system_events (
    event_type TEXT,
    event_data TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Settings Groups (for 16×2 LCD)
1. Temperature unit (C/F)
2. Alarm (on/off + time + weekday/weekend profiles)
3. Log interval (minutes)
4. API fetch interval (minutes)
5. Buzzer mode (ALL/ERR/MUTE)
6. Backlight / auto-dim
7. Auto-scroll
8. High/Low temperature alerts
9. High/Low humidity alerts
10. Sensor offset calibration
11. Quiet hours
12. Location (lat/lon)
13. Factory reset

### Implementation Status
✅ **DATABASE LAYER COMPLETE**
- `save_setting(key, value, modified_by)` tracks origin
- `get_all_settings()` returns dict with metadata
- `export_config()` / `import_config()` for backup

### Remaining Work
- Expand LCD settings menu in `display/widgets.py`
- Build grouped settings UI in web dashboard
- Add import/export endpoints to web API

---

## 4. LCD Layout & Interaction Polish

### Page Layout (Standard)
| Page | Widget | Line 1 | Line 2 |
|------|--------|--------|--------|
| 1 | Clock | `Time: HH:MM:SS` | `Date: DD-MM-YY` |
| 2 | Indoor | `In:24.5C→ H:45%` | `State: Comfort :)` |
| 3 | Outdoor | `Out:28.1C 40%` | `Fcst: ☀️ Clear` |
| 4 | Forecast | `L:22.0 H:30.5` | `UV:3.2 P:5.1` |
| 5 | AQI | `AQI:42 (OK)` | `P2.5:12 P10:20` |
| 6 | Moon | `Moon: 🌕 Full` | `Illum: 98%` |

### AQI Status Words (abbreviated, never truncated)
- `OK` (0-50)
- `Mod` (51-100)
- `Sens` (101-150)
- `Unhl` (151-200)
- `VUnh` (201-300)
- `Hazd` (301+)

### Gesture Standardization
| Action | Duration | Result |
|--------|----------|--------|
| Tap | < 0.6s | Next page / next setting |
| Triple tap | 3 taps in 1s | Enter/leave settings |
| Short hold | 3s | Change value (in settings) |
| Medium hold | 5s | Reboot (with countdown) |
| Long hold | 10s | Shutdown (with countdown) |

### Boot Sequence
1. Branded splash: "WEATHER STATION v3.0 Booting..."
2. Loading bar with custom char blocks
3. Sensor check (DHT11)
4. WiFi/API check
5. First widget page

### Idle Behavior
- Auto-dim after configurable period (default 300s)
- Wake on any button press
- Smooth transitions (no jumping)

### Implementation Status
⚠️ **PARTIAL** - Basic widgets exist, need:
- Moon phase icon animation
- Sunrise/sunset calculation
- Feels-like temperature
- Station uptime widget
- Gesture refinement in `input/processor.py`
- Boot splash polish in `main.py`

---

## 5. Web UI – Professional Look & Feel

### Current State
✅ Templates exist in `/workspace/src/weather_station/web/templates/`:
- `dashboard.html` - Live metrics grid + LCD mirror
- `designer.html` - Screen designer (placeholder)
- `settings.html` - Basic form (needs expansion)

✅ CSS design system in `/workspace/src/weather_station/web/static/style.css`:
- CSS variables for colors, spacing, typography
- Dark mode support
- Card, badge, button components
- LCD preview styling
- Loading skeletons

### Required Enhancements

#### Navigation
- Persistent sidebar or top nav with live mini-status
- Connection indicator (green/amber/red dot)
- Command palette (Ctrl+K) for power users

#### Live Updates
- WebSocket already implemented in `web/app.py`
- Add subtle number transitions (count-up animation)
- Severity color changes on metric tiles

#### Settings Page
- Collapsible sections matching LCD groups
- Toggles, steppers, text inputs as appropriate
- Instant "Saved" toast notifications
- No full page reloads (AJAX/fetch)
- Show "last modified by (user) at (time)"

#### Footer
Always show:
- Version number
- Uptime
- Last data age ("API 3m ago")

#### PWA Support
Add manifest.json for installable web app:
```json
{
  "name": "SkyCast Weather Station",
  "short_name": "SkyCast",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#0288d1",
  "background_color": "#f4f7f6"
}
```

### Implementation Status
⚠️ **PARTIAL** - Foundation exists, needs:
- Sidebar navigation component
- Settings page redesign with grouped sections
- Toast notification system
- PWA manifest and service worker
- Empty/loading/error states

---

## 6. Discord Bot – Complete Professional Behaviour

### Current State
✅ Basic bot structure in `/workspace/src/weather_station/services/discord_bot.py`:
- Slash commands: `/status`, `/now`, `/health`, `/help`, `/about`
- Natural language DM handling
- Conversation memory (per-user)
- Rich embeds with brand color
- Daily briefing task
- Presence updates

### Missing Components

#### First-Join Wizard
When bot joins a server:
1. Confirm/select weather station location
2. Choose default alerts channel
3. Select roles allowed to run control commands
4. Enable/disable natural-language chat
5. Optional: daily briefing time and channel

Use Discord UI components:
- Buttons for yes/no choices
- Select menus for channel/role selection
- Store results in `discord_servers` table

#### Per-Server Settings
```python
{
    "server_id": "123456789",
    "channel_id": "987654321",
    "allowed_roles": ["Admin", "Weather Watcher"],
    "nl_enabled": True,
    "briefing_hour": 7,
    "quiet_hours_start": 22,
    "quiet_hours_end": 7
}
```

#### Per-User Settings
```python
{
    "user_id": "111222333",
    "preferred_units": "F",
    "dm_briefing_enabled": True,
    "custom_thresholds": {"temp_high": 35, "aqi_alert": 100}
}
```

#### Natural Language Improvements
- Editable persona prompt stored in config
- Deterministic intent matching first (regex/patterns)
- Only ambiguous messages go to LLM
- Short per-user memory (last 5 turns)
- Polite redirect to slash commands when NL disabled

#### Security
- Owner ID checks for dangerous commands
- Role-based permissions
- All state-changing actions logged to `system_events`
- Token only from environment variables

### Implementation Status
⚠️ **PARTIAL** - Core bot works, needs:
- First-join wizard with UI components
- Per-server/per-user database integration
- Enhanced NL intent matching
- Confirmation modals for dangerous actions
- Better error handling and logging

---

## 7. Update Checking (GitHub)

### Background Task
```python
async def check_github_updates():
    """Query GitHub Releases API once per day."""
    url = f"https://api.github.com/repos/{settings.github_repo}/releases/latest"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            latest = data['tag_name'].lstrip('v')
            current = __version__
            
            if semver.compare(latest, current) > 0:
                await db.save_update_check(
                    current_version=current,
                    latest_version=latest,
                    release_notes=data.get('body', ''),
                    update_available=True
                )
                # Optionally notify Discord
```

### User-Facing Features
- Badge on web dashboard (visible if update available)
- Optional Discord notification (respecting quiet hours)
- Release notes displayed cleanly
- One-click update path (with checksum verification)
- Manual update instructions as fallback

### Implementation Status
❌ **NOT STARTED** - Need to create:
- `services/update_checker.py` module
- Background task in `main.py`
- Web endpoint `/api/update-status`
- Discord command `/check-updates`
- Database integration (schema ready)

---

## 8. Reliability, Observability & Professional Trust

### Health Endpoint
✅ Partially exists - needs expansion:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "ok" if all(subsystems_ok) else "degraded",
        "subsystems": {
            "database": db_status,
            "sensors": sensor_status,
            "api": api_status,
            "discord": discord_status,
            "lcd": lcd_status
        },
        "uptime_seconds": (datetime.now() - state.startup_time).total_seconds(),
        "version": __version__,
        "last_api_fetch": state.last_api_fetch.isoformat() if state.last_api_fetch else None
    }
```

### Automatic Recovery
- Retry logic for transient sensor failures
- Quiet logging (don't spam on known issues)
- Graceful degradation (show cached data if API down)

### Database Maintenance
- Retention policy (keep N days of logs)
- Periodic VACUUM (weekly)
- Size monitoring + alerts

### Graceful Shutdown
1. Clear LCD display
2. Stop buzzer
3. Close database connections
4. Log shutdown event
5. Exit cleanly

### Support Bundle Export
Endpoint: `/api/export-support-bundle`
Returns sanitized ZIP containing:
- Recent logs (last 100 lines)
- Current config (redacted secrets)
- Version info
- System stats
- Last 50 system events

### Implementation Status
⚠️ **PARTIAL** - Need:
- Expanded `/health` endpoint
- Retry decorators for services
- Database retention policy
- Support bundle export function
- Better shutdown handling

---

## 9. Onboarding & Documentation

### First-Run Web Wizard
Guide new users through:
1. Location selection (map or manual lat/lon)
2. Unit preference (C/F)
3. Alert thresholds
4. Discord token (optional)
5. Test notifications

### Product Tour
Interactive overlay for first-time web visitors:
- Highlight key features
- Explain live updates
- Show settings location
- Link to documentation

### README Improvements
Current README is good. Add:
- Screenshots of all three surfaces (LCD, web, Discord)
- 3-minute "happy path" quickstart
- Badges for version, license, Python version
- Architecture diagram
- "Running without hardware" section

### Documentation Site
Use same visual language:
- Architecture notes
- Widget reference
- API description
- Troubleshooting guide
- FAQ

### Implementation Status
⚠️ **PARTIAL** - README exists, needs:
- First-run wizard (web + Discord)
- Interactive product tour
- Documentation site setup
- Screenshots and diagrams

---

## 10. Packaging & Distribution

### pyproject.toml
✅ **COMPLETED** - Full modern configuration:
- Build system specification
- Project metadata
- Dependencies with platform markers
- Console script entry points
- Tool configurations (black, ruff, myypy, pytest)

### Installation Options

#### One-Line Installer (Raspberry Pi)
```bash
curl -sSL https://raw.githubusercontent.com/user/repo/main/install.sh | bash
```
Script should:
- Create system user `skycast`
- Install Python dependencies
- Copy config files
- Enable systemd service
- Start the service

#### systemd Unit
```ini
[Unit]
Description=SkyCast Weather Station
After=network.target

[Service]
Type=simple
User=skycast
WorkingDirectory=/opt/skycast
ExecStart=/opt/skycast/venv/bin/python -m weather_station.main
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Docker Compose
```yaml
version: '3.8'
services:
  skycast:
    build: .
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    environment:
      - WEATHER_DISCORD_TOKEN=${DISCORD_TOKEN}
    ports:
      - "8000:8000"
    restart: unless-stopped
```

### Pre-built Artifacts
- GitHub Releases with source tarballs
- Checksums (SHA256) for all artifacts
- Wheel packages for easy installation

### Implementation Status
✅ **PYPROJECT COMPLETE**
❌ **INSTALLER/DOCKER MISSING** - Need to create:
- `install.sh` script
- `skycast.service` systemd unit
- `Dockerfile` and `docker-compose.yml`
- GitHub Actions workflow for releases

---

## 11. Implementation Order for Maximum Impact

### Phase 1: Foundation (Week 1)
1. ✅ Lock design system (CSS variables, colors)
2. ✅ Apply to web templates + Discord embeds
3. ✅ Expand database schema
4. ⏳ Finish settings persistence (hardware menu + web page)

### Phase 2: Discord Enhancement (Week 2)
5. ⏳ First-join wizard
6. ⏳ Per-server/per-user storage
7. ⏳ Natural language improvements
8. ⏳ Confirmation modals for dangerous actions

### Phase 3: Web UI Polish (Week 3)
9. ⏳ Sidebar navigation with live status
10. ⏳ Metric tiles with transitions
11. ⏳ Settings redesign (grouped, instant save)
12. ⏳ PWA manifest + service worker

### Phase 4: LCD & Input (Week 4)
13. ⏳ Boot splash refinement
14. ⏳ Gesture finalization
15. ⏳ Idle dimming behavior
16. ⏳ Additional widgets (moon phase animation, uptime)

### Phase 5: Reliability & Distribution (Week 5)
17. ❌ Update checker
18. ❌ Health endpoint expansion
19. ❌ Support bundle export
20. ❌ Packaging (installer, Docker, systemd)

### Phase 6: Documentation & Launch (Week 6)
21. ❌ First-run wizards
22. ❌ Product tour
23. ❌ Documentation site
24. ❌ Final README polish
25. ❌ Public repository cleanup

---

## Appendix A: File Change Summary

### Modified Files
| File | Changes | Status |
|------|---------|--------|
| `__init__.py` | Added VERSION, PROJECT_NAME, TAGLINE | ✅ |
| `core/state.py` | Added settings tracking, Discord state | ✅ |
| `core/config.py` | Full Pydantic validation, expanded fields | ✅ |
| `persistence/models.py` | 7 database tables | ✅ |
| `persistence/database.py` | 20+ methods for all operations | ✅ |
| `main.py` | Clean entry point, data logger task | ✅ |
| `pyproject.toml` | Complete modern packaging | ✅ |

### Files Needing Updates
| File | Required Changes | Priority |
|------|-----------------|----------|
| `display/widgets.py` | Expand settings menu, add widgets | High |
| `input/processor.py` | Refine gestures, triple-tap | High |
| `web/app.py` | Settings endpoints, health endpoint | High |
| `web/templates/settings.html` | Grouped sections, instant save | High |
| `services/discord_bot.py` | First-join wizard, per-server logic | High |
| `services/update_checker.py` | CREATE NEW | Medium |
| `README.md` | Screenshots, architecture diagram | Medium |

---

## Appendix B: Environment Variables Reference

```bash
# Location
WEATHER_LATITUDE=29.325390
WEATHER_LONGITUDE=48.019562
WEATHER_TIMEZONE=UTC

# Display
WEATHER_UNIT=C
WEATHER_LANGUAGE=en
WEATHER_THEME=auto

# Hardware
WEATHER_BUZZER_MODE=ALL
WEATHER_DHT_TEMP_OFFSET=0.0
WEATHER_DHT_HUMID_OFFSET=0.0
WEATHER_IDLE_TIMEOUT=300

# Timing
WEATHER_API_RATE=10
WEATHER_LOG_RATE=15

# Web Server
WEATHER_WEB_HOST=0.0.0.0
WEATHER_WEB_PORT=8000

# Database
WEATHER_DB_FILE=weather_history.db

# Discord
WEATHER_DISCORD_TOKEN=your_token_here
WEATHER_DISCORD_CHANNEL_ID=123456789
WEATHER_DISCORD_OWNER_IDS=[111111,222222]

# Alerts
WEATHER_ALERT_ENABLED=false
WEATHER_ALERT_HOUR=17
WEATHER_ALERT_MINUTE=0
WEATHER_QUIET_HOURS_START=22
WEATHER_QUIET_HOURS_END=7

# Thresholds
WEATHER_TEMP_HIGH_ALERT=35.0
WEATHER_TEMP_LOW_ALERT=5.0
WEATHER_HUMID_HIGH_ALERT=70.0
WEATHER_HUMID_LOW_ALERT=30.0

# Updates
WEATHER_CHECK_UPDATES=true
WEATHER_GITHUB_REPO=yourusername/weather-station
```

---

## Conclusion

The SkyCast Weather Station has a solid foundation for becoming a truly professional, polished product. The core architecture is sound, the design system is defined, and the database layer is comprehensive. 

**Next immediate priorities:**
1. Expand the LCD settings menu to match the 13 groups
2. Build the grouped settings UI for web dashboard
3. Implement Discord first-join wizard
4. Create update checker service
5. Write installer script and Docker configuration

With focused effort over 4-6 weeks following this implementation order, the project will achieve the "deliberate product" feel described in the original recommendations.
