"""Raspberry Pi Hardware Diagnostic Metrics."""
import psutil

def get_pi_stats() -> dict:
    cpu_usage = f"{psutil.cpu_percent():.1f}%"
    ram_usage = f"{psutil.virtual_memory().percent:.1f}%"
    
    cpu_temp = "N/A"
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_raw = float(f.read().strip())
            cpu_temp = f"{temp_raw / 1000.0:.1f}°C"
    except Exception:
        pass

    return {
        "pi_cpu_temp": cpu_temp,
        "pi_cpu_usage": cpu_usage,
        "pi_ram_usage": ram_usage
    }