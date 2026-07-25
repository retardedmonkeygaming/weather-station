"""Background service for monitoring threshold alerts and sending webhooks."""
import asyncio
import aiohttp
from core.state import state


async def check_alerts_loop():
    """Continuously evaluates sensor data against high/low thresholds."""
    last_alert_time = 0
    cooldown_seconds = 600  # Prevent notification spam (10 min cooldown)

    while True:
        await asyncio.sleep(30)
        snap = state.get_snapshot_sync()
        
        if not snap.webhook_url:
            continue

        temp = snap.indoor_temp
        if temp is None:
            continue

        triggered = False
        msg = ""

        if temp >= snap.high_temp_threshold:
            triggered = True
            msg = f"⚠️ WEATHER ALERT: High indoor temperature detected! {temp:.1f}C (Threshold: {snap.high_temp_threshold}C)"
        elif temp <= snap.low_temp_threshold:
            triggered = True
            msg = f"⚠️ WEATHER ALERT: Low indoor temperature detected! {temp:.1f}C (Threshold: {snap.low_temp_threshold}C)"

        if triggered:
            now = asyncio.get_event_loop().time()
            if now - last_alert_time > cooldown_seconds:
                last_alert_time = now
                asyncio.create_task(send_webhook(snap.webhook_url, msg))


async def send_webhook(url: str, message: str):
    """Dispatches webhook POST request."""
    payload = {"content": message}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=5) as resp:
                if resp.status >= 400:
                    print(f"[WEBHOOK ERROR]: Status code {resp.status}")
    except Exception as e:
        print(f"[WEBHOOK EXCEPTION]: {e}")