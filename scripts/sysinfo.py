# ~/work/scripts/sysinfo.py
import socket, shutil
def cpu_temp():
    p = '/sys/class/thermal/thermal_zone0/temp'
    with open(p) as f:
        return int(f.read()) / 1000

host = socket.gethostname()
free_gb = shutil.disk_usage('/').free / 1024**3
print(f"host={host} temp={cpu_temp():.1f}C "f"disk_free={free_gb:.1f}GB")