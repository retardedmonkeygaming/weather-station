"""
system_health.py — Pi system diagnostics for the web health dashboard.

Reads (all desktop-safe; values degrade to "N/A" off-Pi instead of raising):
    * CPU temperature   — /sys/class/thermal/thermal_zone0/temp
    * CPU usage         — /proc/stat instantaneous sample
    * RAM usage         — /proc/meminfo (used/total + percent)
    * Disk usage        — shutil.disk_usage on the project filesystem
    * IP address        — UDP socket probe (no packets sent)
    * Uptime            — /proc/uptime
    * WiFi signal       — `iwconfig` or `nmcli` signal quality
"""

from __future__ import annotations

import logging
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

import config

log = logging.getLogger("weather.system_health")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_cpu_temp() -> str:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return f"{float(f.read().strip()) / 1000.0:.1f}C"
    except Exception:
        return "N/A"


def get_cpu_usage() -> str:
    try:
        with open("/proc/stat") as f:
            fields = [float(c) for c in f.readline().strip().split()[1:]]
        idle, total = fields[3], sum(fields)
        return f"{100.0 * (1.0 - idle / total):.1f}%"
    except Exception:
        return "N/A"


def get_ram_usage() -> Dict[str, str]:
    """Return {"used": "412/925MB", "percent": "44.5%"} style values."""
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem_total = int(lines[0].split()[1])          # MemTotal kB
        mem_available = int(lines[2].split()[1])      # MemAvailable kB
        used = mem_total - mem_available
        pct = 100.0 * used / mem_total
        return {
            "used": f"{used // 1024}/{mem_total // 1024}MB",
            "percent": f"{pct:.1f}%",
        }
    except Exception:
        return {"used": "N/A", "percent": "N/A"}


def get_disk_usage() -> Dict[str, str]:
    """Return {"used": "12/64GB", "percent": "18.8%"} for the project fs."""
    try:
        total, used, _free = shutil.disk_usage(str(_PROJECT_ROOT))
        pct = 100.0 * used / total
        return {
            "used": f"{used // (2**30)}/{total // (2**30)}GB",
            "percent": f"{pct:.1f}%",
        }
    except Exception:
        return {"used": "N/A", "percent": "N/A"}


def get_ip_address() -> str:
    """Primary outbound IPv4 via a connected UDP socket (no packets sent)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return "N/A"


def get_uptime() -> str:
    """Host uptime from /proc/uptime, else process uptime."""
    try:
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
    except Exception:
        secs = int(time.time() - config.get_state().started_at)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def get_wifi_signal() -> str:
    """WiFi RSSI/quality via iwconfig, falling back to nmcli (Pi-only)."""
    # --- iwconfig: "Signal level=-52 dBm" or "Signal level=58/70" ---
    try:
        out = subprocess.run(
            ["iwconfig"], capture_output=True, text=True, timeout=3,
        ).stdout
        m = re.search(r"Signal level[=:]\s*(-?\d+)\s*dBm", out)
        if m:
            return f"{m.group(1)} dBm"
        m = re.search(r"Signal level[=:]\s*(\d+)/(\d+)", out)
        if m:
            quality = 100.0 * int(m.group(1)) / int(m.group(2))
            return f"{quality:.0f}%"
    except Exception:
        pass
    # --- nmcli: "in-use" row's SIGNAL column (0-100) ---
    try:
        out = subprocess.run(
            ["nmcli", "-t", "-f", "IN-USE,SIGNAL", "dev", "wifi"],
            capture_output=True, text=True, timeout=3,
        ).stdout
        for line in out.splitlines():
            if line.startswith("*:"):
                return f"{line.split(':', 1)[1].strip()}%"
    except Exception:
        pass
    return "N/A"


def collect_system_health() -> Dict[str, Any]:
    """One snapshot for /api/system and the dashboard health card."""
    ram = get_ram_usage()
    disk = get_disk_usage()
    state = config.get_state()
    return {
        "cpu_temp": get_cpu_temp(),
        "cpu_usage": get_cpu_usage(),
        "ram_used": ram["used"],
        "ram_percent": ram["percent"],
        "disk_used": disk["used"],
        "disk_percent": disk["percent"],
        "ip_address": get_ip_address(),
        "uptime": get_uptime(),
        "wifi_signal": get_wifi_signal(),
        "wifi_connected": not state.wifi_error,
        "dht_ok": not state.dht_error,
        "lcd_mock": None,   # filled by the route (avoids import cycle)
        "subsystems": config.subsystem_status(),
        "version": config.APP_VERSION,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
