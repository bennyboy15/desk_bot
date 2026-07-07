import platform
import gputil
import psutil
import cpuinfo

# === OS & Architecture ===
print(f"--- Operating System ---")
print(f"OS/Platform: {platform.system()}")
print(f"OS Version: {platform.version()}")
print(f"Architecture: {platform.machine()}\n")

# === CPU Information ===
print(f"--- CPU Details ---")
# py-cpuinfo gets the exact commercial name (e.g., Intel Core i7)
print(f"Processor Name: {cpuinfo.get_cpu_info()['brand_raw']}")
print(f"Physical Cores: {psutil.cpu_count(logical=False)}")
print(f"Total (Logical) Cores: {psutil.cpu_count(logical=True)}")
print(f"Current Frequency: {psutil.cpu_freq().current:.2f} MHz\n")

# === RAM / Memory ===
print(f"--- Memory / RAM ---")
virtual_mem = psutil.virtual_memory()
print(f"Total RAM: {virtual_mem.total / (1024**3):.2f} GB")
print(f"Available RAM: {virtual_mem.available / (1024**3):.2f} GB\n")

# === Storage / Disks ===
print(f"--- Storage Disks ---")
for partition in psutil.disk_partitions():
    try:
        usage = psutil.disk_usage(partition.mountpoint)
        print(f"Mountpoint: {partition.mountpoint} ({partition.fstype})")
        print(f"  Total Space: {usage.total / (1024**3):.2f} GB")
        print(f"  Used Space: {usage.used / (1024**3):.2f} GB")
    except PermissionError:
        continue
