# 🌤️ SkyCast Weather Station

> **Professional-grade environmental monitoring for Raspberry Pi**  
> *Your window to the weather — indoors and out*

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/yourusername/weather-station)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Hardware](https://img.shields.io/badge/hardware-Raspberry_Pi-red.svg)](https://raspberrypi.org)

---

## 📖 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Hardware Requirements](#hardware-requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Web Dashboard](#web-dashboard)
- [Discord Bot](#discord-bot)
- [LCD Display](#lcd-display)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

SkyCast is a **complete, production-ready weather station** built for Raspberry Pi. It combines local sensor data (DHT11) with outdoor forecasts (Open-Meteo API) and air quality metrics, presenting them across three synchronized surfaces:

1. **Physical LCD** — 16x2 character display with custom widgets
2. **Web Dashboard** — Modern, responsive interface with live updates
3. **Discord Bot** — Chat-based queries and proactive alerts

Designed with a **unified visual identity** and professional UX patterns throughout, SkyCast feels polished, trustworthy, and pleasant to use every day.

---

## ✨ Features

### 🌡️ Multi-Source Weather Data
- **Indoor**: Temperature & humidity via DHT11 sensor
- **Outdoor**: Forecast from Open-Meteo API (no key required)
- **Air Quality**: US AQI, PM2.5, PM10 from Open-Meteo Air Quality API
- **UV Index**: Current and daily maximum

### 🖥️ Triple-Surface Display
| Surface | Description |
|---------|-------------|
| **LCD 1602** | 16x2 character display with 10+ widget types, gesture navigation, and settings menu |
| **Web UI** | Responsive dashboard with metric cards, live LCD mirror, history tables, and screen designer |
| **Discord** | Slash commands (`/status`, `/now`), natural-language DMs, rich embeds, and alert notifications |

### 🔔 Smart Alerts & Feedback
- **Dual Buzzer System**: Active buzzer (GPIO 6) for beeps, passive buzzer (GPIO 16) for tones/melodies
- **Configurable Modes**: ALL, ERR (errors only), MUTE
- **Touch Input**: Single tap (next page), long press (reboot/shutdown), hold (settings)

### 🎨 Professional Design System
- **Primary Color**: `#0288d1` (Material Blue)
- **Status Colors**: Green (success), Amber (warning), Red (error)
- **Dark Mode**: Automatic or manual toggle
- **Consistent Typography**: Segoe UI / system fonts with proper scale
- **Micro-interactions**: Hover lifts, smooth transitions, skeleton loaders

### 🛠️ Developer Experience
- **Modular Architecture**: Clean separation of concerns (hardware, services, web, display)
- **Type Hints**: Full Python typing for IDE support
- **Async First**: Built on `asyncio` for concurrent operations
- **Environment Config**: `.env` file or `WEATHER_` prefixed env vars
- **SQLite History**: Persistent logging with configurable intervals

---

## 🔧 Hardware Requirements

| Component | Model | GPIO Pin | Notes |
|-----------|-------|----------|-------|
| **Raspberry Pi** | Any (3B+/4/Zero recommended) | — | Requires GPIO header |
| **LCD 1602A** | HD44780 (I2C or parallel) | RS=22, EN=17, D4=25, D5=24, D6=23, D7=18 | I2C backpack simplifies wiring |
| **DHT11** | Temperature/Humidity Sensor | GPIO 4 | Add 10k pull-up resistor |
| **Active Buzzer** | 3-5V DC Buzzer | GPIO 6 | For simple beeps |
| **Passive Buzzer** | PWM-driven Speaker | GPIO 16 | For tones/melodies |
| **Touch Button** | Momentary Switch | GPIO 27 | For navigation |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/weather-station.git
cd weather-station
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file in the project root:

```env
# Location (Kuwait City default)
WEATHER_LATITUDE=29.325390
WEATHER_LONGITUDE=48.019562

# Units
WEATHER_UNIT=C
WEATHER_LANGUAGE=en

# Hardware
WEATHER_BUZZER_MODE=ALL  # ALL, ERR, MUTE

# Discord (optional)
WEATHER_DISCORD_TOKEN=your_bot_token_here
WEATHER_DISCORD_CHANNEL_ID=1234567890

# Timing (minutes)
WEATHER_API_RATE=10
WEATHER_LOG_RATE=15

# Web Server
WEATHER_WEB_HOST=0.0.0.0
WEATHER_WEB_PORT=8000

# UI
WEATHER_THEME=auto  # light, dark, auto
```

### 3. Run

```bash
python -m src.weather_station.main
```

---

## ⚙️ Configuration

### Settings Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `WEATHER_LATITUDE` | `29.325390` | Latitude for API queries |
| `WEATHER_LONGITUDE` | `48.019562` | Longitude for API queries |
| `WEATHER_UNIT` | `C` | Temperature unit: `C` or `F` |
| `WEATHER_BUZZER_MODE` | `ALL` | Sound mode: `ALL`, `ERR`, `MUTE` |
| `WEATHER_API_RATE` | `10` | Minutes between API fetches |
| `WEATHER_LOG_RATE` | `15` | Minutes between DB logs |
| `WEATHER_IDLE_TIMEOUT` | `300` | Seconds before LCD dims |
| `WEATHER_THEME` | `auto` | UI theme: `light`, `dark`, `auto` |
| `WEATHER_DISCORD_TOKEN` | — | Discord bot token |

---

## 🌐 Web Dashboard

Access at `http://<pi-ip>:8000`

### Pages

| Route | Description |
|-------|-------------|
| `/` | Live dashboard with metric cards and recent history |
| `/designer` | Drag-and-drop LCD screen designer |
| `/settings` | System configuration and calibration |
| `/logs` | Full historical data table |
| `/health` | System health check (JSON) |

---

## 🤖 Discord Bot

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/status` | Full weather report embed | `/status` |
| `/now` | Quick current conditions | `/now` |
| `/aqi` | Air quality details | `/aqi` |
| `/help` | Interactive help menu | `/help` |
| `/health` | Bot latency & subsystem status | `/health` |

### Natural Language (DMs)

Bot responds conversationally in DMs or `#station-chat`:

```
You: how's it looking inside?
Bot: It's currently **23.4°C** inside with **45%** humidity.

You: what about outside?
Bot: The outdoor temperature is **28.1°C**. It is **Clear**.

You: aqi?
Bot: The Air Quality Index is **42** (Good).
```

---

## 📟 LCD Display

### Widget Types

| Widget | Line 1 | Line 2 |
|--------|--------|--------|
| Indoor Climate | `In:23.4C→ H:45%` | `State: Comfort` |
| Outdoor Weather | `Out:28.1C 40%` | `Fcst: Clear` |
| Moon Phase | `Moon: Full` | `Illum: 98%` |
| Air Quality | `AQI:42 (Good)` | `P2.5:12 P10:20` |
| Pi System | `CPU:45.2C 12%` | `RAM:34%` |
| Clock | `Time: 14:30:00` | `Date: 15-01-24` |

### Navigation

| Action | Result |
|--------|--------|
| **Tap** (< 0.6s) | Next page / next setting |
| **Hold** (3s) | Enter settings |
| **Hold** (5s) | Reboot system |
| **Hold** (10s) | Shutdown Pi |

---

## 📡 API Reference

### GET /api/data

Live sensor and LCD state.

```json
{
  "lcd_line1": "In:23.4C-> H:45%",
  "indoor_temp": "23.4C",
  "outdoor_temp": "28.1C",
  "aqi_val": "42"
}
```

### GET /health

System health summary.

```json
{
  "status": "ok",
  "uptime_seconds": 86400,
  "version": "3.0.0"
}
```

---

## 🐛 Troubleshooting

### DHT11 Reading None
- Check wiring (GPIO 4, 5V, GND)
- Add 10k pull-up resistor

### LCD Shows Garbage
- Verify pin mapping in `pins.py`
- Adjust contrast potentiometer

### Discord Bot Not Responding
- Confirm token in `.env`
- Enable Message Content Intent

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch
3. Commit changes
4. Push and open PR

---

## 📄 License

MIT License — see LICENSE for details.

---

**Built with ❤️ by the Weather Station Team**
