import re
import psutil
import cpuinfo
import serial
import time

#arduino = serial.Serial('COM6', 115200, timeout=1)
arduino = serial.Serial('ttyACM0', 115200, timeout=1)
time.sleep(2)

def send(cmd):
    arduino.write((cmd + "\n").encode())

def shortCpuName():
    raw = cpuinfo.get_cpu_info()['brand_raw']
    name = re.sub(r"\((R|TM)\)|CPU|Processor|@.*", "", raw)
    return " ".join(name.split())[:21]   # 21 chars is the display's width

if __name__ == "__main__":
    processorName = shortCpuName()   # hoisted: get_cpu_info() spawns a subprocess
    send("mode stats")
    psutil.cpu_percent()             # first call always returns 0.0 — prime it

    while True:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        line = f"{processorName},{cpu:.1f},{ram:.1f}"
        send(line)
        print(line)
        time.sleep(1)
