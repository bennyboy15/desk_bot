import platform
import psutil
import cpuinfo
import serial
import time

# === Mount serial communication ===
arduino = serial.Serial('COM5', 9600, timeout=1)
#arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1) LINUX
time.sleep(2)  # Uno resets on serial connect — wait for it to boot

# === CPU Info ===
def getCpuInfo():
    processorName = cpuinfo.get_cpu_info()['brand_raw']
    cores = psutil.cpu_count(logical=False)
    frequency = psutil.cpu_freq().current # MHz
    return processorName,cores,frequency

# === OS & Architecture ===
def getOsInfo():
    osPlatform = platform.system()
    osVersion = platform.version()
    architecture = platform.machine()
    return osPlatform, osVersion, architecture

# === RAM Info ===
def getRamInfo():
    virtual_mem = psutil.virtual_memory()
    totalRam = virtual_mem.total / (1024**3) # GB
    availRam = virtual_mem.available / (1024**3) # GB
    return virtual_mem, totalRam, availRam


if __name__ == "__main__":
    while(1):
        processorName,cores,frequency = getCpuInfo()
        osPlatform, osVersion, architecture = getOsInfo()
        virtual_mem, totalRam, availRam = getRamInfo()

        serialLine = f"{processorName} {cores} {frequency},"
        #serialLine += f"{osPlatform},{osVersion},{architecture},"
        #serialLine += f"{virtual_mem},{totalRam},{availRam}"
        serialLine += f"{totalRam}, {availRam}"
        arduino.write(serialLine.encode())
        print(serialLine)
        time.sleep(5)
        