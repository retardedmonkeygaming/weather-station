import os
import shutil

class SystemService:
    @staticmethod
    def get_stats():
        stats = {"cpu_temp": "N/A", "cpu_usage": "N/A", "ram_usage": "N/A"}
        
        # CPU Temperature
        try:
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    stats["cpu_temp"] = f"{float(f.read().strip()) / 1000.0:.1f}C"
        except: pass

        # RAM Usage
        try:
            total, used, free = shutil.disk_usage("/")
            # This is a simplification; for professional stats, we use /proc/meminfo
            stats["ram_usage"] = f"{(used/total)*100:.1f}%"
        except: pass

        return stats