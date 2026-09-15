"""
weather_api.py — outbound async HTTP for Open-Meteo weather & air quality.

Clean separation: pure `parse_*` functions turn JSON payloads into typed
dicts; the fetch loop only orchestrates sessions, error accounting, and poll
cadence. Any failure marks wifi_error in shared state instead of crashing.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

import config
from config import get_state

log = logging.getLogger("weather.api")

# ---------------------------------------------------------------------------
# Pure parsers (no I/O — trivially unit-testable)
# ---------------------------------------------------------------------------

def parse_forecast_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract current + daily values from an Open-Meteo forecast payload."""
    parsed: Dict[str, Any] = {}
    current = data.get("current", {})
    if current:
        parsed["outdoor_temp"] = f"{float(current['temperature_2m']):.1f}"
        parsed["outdoor_humid"] = str(int(current["relative_humidity_2m"]))
        parsed["uv_current"] = f"{float(current['uv_index']):.1f}"
        parsed["weather_code"] = int(current.get("weather_code", 0))

    daily = data.get("daily", {})
    if daily:
        parsed["outdoor_max"] = f"{float(daily['temperature_2m_max'][0]):.1f}"
        parsed["outdoor_min"] = f"{float(daily['temperature_2m_min'][0]):.1f}"
        parsed["uv_max"] = f"{float(daily['uv_index_max'][0]):.1f}"

    return parsed


def aqi_status_label(aqi: int) -> str:
    """Short human label for a US AQI integer (fits a 16-col LCD)."""
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Sensitiv"
    if aqi <= 200:
        return "Unhealth"
    if aqi <= 300:
        return "V.Unhlth"
    return "Hazard"


def parse_aqi_payload(data: Dict[str, Any]) -> Dict[str, str]:
    """Extract US AQI + particulate matter values from an AQI payload."""
    current = data.get("current", {})
    if not current:
        return {}
    return {
        "aqi_val": str(int(current["us_aqi"])),
        "aqi_status": aqi_status_label(int(current["us_aqi"])),
        "pm2_5_val": str(int(current["pm2_5"])),
        "pm10_val": str(int(current["pm10"])),
    }


def weather_info(code: int) -> tuple:
    """Map an Open-Meteo weather_code to (custom_glyph, short_text).

    Glyphs reference the burn-once CGRAM table (\\x04 cloud, \\x05 sun).
    """
    if code in (0, 1):
        return ("\x05", "Clear")
    if code in (2, 3):
        return ("\x04", "Cloudy")
    if code in (45, 48):
        return ("\x04", "Foggy")
    if code in (51, 53, 55, 61, 63, 65):
        return ("\x04", "Rain")
    if code in (71, 73, 75):
        return ("\x04", "Snow")
    if code in (95, 96, 99):
        return ("\x04", "Storm")
    return ("\x05", "Clear")


# ---------------------------------------------------------------------------
# Fetch loop
# ---------------------------------------------------------------------------

async def _fetch_json(session: aiohttp.ClientSession,
                      url: str) -> Optional[Dict[str, Any]]:
    """GET JSON with a hard timeout; None on any failure."""
    try:
        async with session.get(url) as response:
            if response.status != 200:
                log.warning("GET %s -> HTTP %s", url, response.status)
                return None
            return await response.json()
    except Exception as exc:
        log.warning("GET %s failed: %s", url, exc)
        return None


async def _apply_forecast(state, session: aiohttp.ClientSession,
                          url: str) -> bool:
    data = await _fetch_json(session, url)
    if data is None:
        return False
    for key, value in parse_forecast_payload(data).items():
        setattr(state, key, value)
    return True


async def _apply_aqi(state, session: aiohttp.ClientSession,
                     url: str) -> bool:
    data = await _fetch_json(session, url)
    if data is None:
        return False
    for key, value in parse_aqi_payload(data).items():
        setattr(state, key, value)
    return True


def _current_urls(state) -> tuple:
    lat = state.get_setting("latitude")
    lon = state.get_setting("longitude")
    return config.build_api_urls(lat, lon)


async def weather_fetch_loop() -> None:
    """Forever-loop fetcher; supervised by main.safe_task.

    Edge-case handling (ENH 4):
        * WiFi drops permanently  — every cycle times out; the loop keeps
          retrying with its own fast retry cadence instead of holding the
          full api_rate interval, marks wifi_error so every UI surface
          shows the offline state, and pushes a notification on the
          transition. Stale data is kept (stale-but-labeled beats blank).
        * Occasional failures      — one failed endpoint doesn't wipe the
          good values from the other; parsing is per-endpoint.
    """
    state = get_state()
    timeout = aiohttp.ClientTimeout(total=config.HTTP_TIMEOUT_SECONDS)

    # Offline retry cadence (fast probe) vs normal api_rate interval.
    OFFLINE_RETRY_S = 30
    consecutive_failures = 0

    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            forecast_url, aqi_url = _current_urls(state)

            ok_forecast = await _apply_forecast(state, session, forecast_url)
            ok_aqi = await _apply_aqi(state, session, aqi_url)
            fetch_failed = not (ok_forecast and ok_aqi)

            if fetch_failed:
                consecutive_failures += 1
            else:
                consecutive_failures = 0

            # Transition handling — notify exactly once per edge, not spam.
            if fetch_failed and not state.wifi_error:
                state.wifi_error = True
                state.mark_page_dirty()
                config.push_notification(
                    "error",
                    "WiFi/API unreachable — showing last known values")
                log.warning("WiFi/API down (consecutive failure #%d)",
                            consecutive_failures)
            elif not fetch_failed and state.wifi_error:
                state.wifi_error = False
                state.mark_page_dirty()
                config.push_notification(
                    "info", "WiFi/API reconnected — live data restored")
                log.info("WiFi/API recovered after %d failed attempts",
                         consecutive_failures if fetch_failed else 0)
                consecutive_failures = 0

            if state.current_page in (3, 4, 5, 6):
                state.mark_page_dirty()

            interval_min = int(state.get_setting("api_rate"))
            sleep_s = (
                OFFLINE_RETRY_S if state.wifi_error
                else max(30, interval_min * 60)
            )
            await asyncio.sleep(sleep_s)
