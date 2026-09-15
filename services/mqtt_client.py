"""
mqtt_client.py — optional MQTT publishing of live station data.

Behavior:
    * Disabled entirely unless MQTT_BROKER is set (env / .env) — the loop
      exits immediately so the supervisor doesn't spin on it.
    * Publishes a JSON snapshot every MQTT_INTERVAL_S to MQTT_TOPIC (+ /status).
    * paho-mqtt client runs on its own thread with reconnect-on-drop;
      `publish_snapshot` is safe to call from the async loop via to_thread.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Dict

import config
from config import get_state

log = logging.getLogger("weather.mqtt")

try:
    import paho.mqtt.client as mqtt
    _PAHO_AVAILABLE = True
except ImportError:
    mqtt = None
    _PAHO_AVAILABLE = False

_client = None
_client_lock = threading.Lock()


def _get_client():
    """Lazily create the shared paho client (single reconnecting thread)."""
    global _client
    if not _PAHO_AVAILABLE or not config.MQTT_BROKER:
        return None
    if _client is None:
        with _client_lock:
            if _client is None:
                try:
                    client = mqtt.Client(
                        client_id=f"weatherstation-{config.PORT}",
                    )
                    client.connect_async(config.MQTT_BROKER, config.MQTT_PORT)
                    client.loop_start()   # background network thread
                    _client = client
                    log.info("MQTT client connecting to %s:%s",
                             config.MQTT_BROKER, config.MQTT_PORT)
                except Exception:
                    log.exception("MQTT client init failed")
                    return None
    return _client


def build_snapshot() -> Dict[str, Any]:
    """Flat JSON-able snapshot of live conditions (MQTT + /api/mqtt shared)."""
    state = get_state()
    from utils import format_temp
    unit = state.get_setting("unit")
    return {
        "indoor_temp": state.indoor_temp,
        "indoor_temp_display": format_temp(state.indoor_temp, unit),
        "indoor_humid": state.indoor_humid,
        "outdoor_temp": state.outdoor_temp,
        "outdoor_humid": state.outdoor_humid,
        "aqi": state.aqi_val,
        "aqi_status": state.aqi_status,
        "unit": unit,
        "lcd_page": state.current_page,
        "lcd_line1": state.last_lcd_rendered_text[0],
        "lcd_line2": state.last_lcd_rendered_text[1],
        "dht_ok": not state.dht_error,
        "wifi_ok": not state.wifi_error,
        "version": config.APP_VERSION,
    }


def publish_snapshot() -> bool:
    """Blocking publish of the current snapshot. Returns success."""
    client = _get_client()
    if client is None:
        return False
    try:
        payload = json.dumps(build_snapshot(), default=str)
        client.publish(config.MQTT_TOPIC, payload, retain=True)
        client.publish(f"{config.MQTT_TOPIC}/status",
                       json.dumps({"online": True,
                                   "ts": config.get_state().started_at}),
                       retain=True)
        return True
    except Exception:
        log.exception("MQTT publish failed")
        return False


async def mqtt_publish_loop() -> None:
    """Supervised forever-loop; exits cleanly when MQTT is not configured."""
    if not _PAHO_AVAILABLE:
        log.info("paho-mqtt not installed — MQTT disabled")
        return
    if not config.MQTT_BROKER:
        log.info("MQTT_BROKER not set — MQTT publishing disabled")
        return
    log.info("MQTT publishing to %s:%s topic '%s' every %ss",
             config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_TOPIC,
             config.MQTT_INTERVAL_S)
    import asyncio
    while True:
        await asyncio.to_thread(publish_snapshot)
        await asyncio.sleep(config.MQTT_INTERVAL_S)
