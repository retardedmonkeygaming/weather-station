import os

class SystemService:
    @staticmethod
    def get_stats():
        cpu_temp = "N/A"
        cpu_usage = "N/A"
        ram_usage = "N/A"
        
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                cpu_temp = f"{float(f.read().strip()) / 1000.0:.1f}C"
            
            # Simple CPU usage via top/loadavg
            load = os.getloadavg()[0]
            cpu_usage = f"{(load / 4) * 100:.1f}%"
            
            # RAM usage
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                total = int(lines[0].split()[1])
                avail = int(lines[2].split()[1])
                ram_usage = f"{((total - avail) / total) * 100:.1f}%"
        except: pass

        return {"cpu_temp": cpu_temp, "cpu_usage": cpu_usage, "ram_usage": ram_usage}