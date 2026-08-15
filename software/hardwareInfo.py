"""PC stats for the bot's stats screen.

Import-safe: this module opens nothing. The daemon uses these functions, and
running it directly sends stats through whatever transport RobotFace finds.
"""

import re
import time

import cpuinfo
import psutil

# 21 characters is what the display fits at text size 1.
NAME_WIDTH = 21


def shortCpuName():
    """Trim the marketing noise out of the CPU model name."""
    raw = cpuinfo.get_cpu_info()["brand_raw"]
    name = re.sub(r"\((R|TM)\)|CPU|Processor|@.*", "", raw)
    return " ".join(name.split())[:NAME_WIDTH]


def primeCpuPercent():
    """psutil's first cpu_percent() always reads 0.0 — burn that call."""
    psutil.cpu_percent()


def statsLine(processorName):
    """One line in the firmware's "<name>,<cpu>,<ram>" format."""
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    return f"{processorName},{cpu:.1f},{ram:.1f}"


if __name__ == "__main__":
    from robotFace import RobotFace

    # get_cpu_info() spawns a subprocess, so read the name once up front.
    processorName = shortCpuName()
    primeCpuPercent()

    with RobotFace() as face:
        face.mode("stats")
        while True:
            line = statsLine(processorName)
            face.send(line)
            print(line)
            time.sleep(1)
