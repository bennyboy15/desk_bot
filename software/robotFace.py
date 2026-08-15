"""Serial link to the desk bot's face.

The firmware exposes two verbs (see hardware/src/main.cpp):
    mode <face|stats|next>   which screen is showing
    face <state|gesture>     what the eyes are doing

States are sticky (idle, listening, thinking, speaking, happy, angry, tired);
gestures are one-shot animations (laugh, confused) that play over whatever
state is current.

The link is optional on purpose: if the bot isn't plugged in, every call turns
into a no-op so a conversation still runs on the PC alone.
"""

import sys
import time

import serial
import serial.tools.list_ports

# The ESP32-C3's native USB CDC. Matching on VID:PID beats a hardcoded port
# name, which differs between machines and moves when other devices enumerate.
ESP32_C3_IDS = [(0x303A, 0x1001)]

BAUD = 115200

# The C3 reboots when the port opens; anything sent before it finishes booting
# is lost.
BOOT_DELAY = 2.0


def findPort():
    """Return the bot's serial device, or None if it isn't connected."""
    for port in serial.tools.list_ports.comports():
        if (port.vid, port.pid) in ESP32_C3_IDS:
            return port.device
    return None


class RobotFace:
    def __init__(self, port=None, quiet=False):
        self.port = port
        self.quiet = quiet
        self.link = None

    def log(self, message):
        if not self.quiet:
            print(message, file=sys.stderr)

    def connect(self):
        port = self.port or findPort()

        if port is None:
            self.log("[face] no bot found — carrying on without it")
            return self

        try:
            self.link = serial.Serial(port, BAUD, timeout=1)
        except serial.SerialException as e:
            # Almost always another process already holding the port.
            self.log(f"[face] could not open {port}: {e}")
            return self

        time.sleep(BOOT_DELAY)
        self.log(f"[face] connected on {port}")
        return self

    def close(self):
        if self.link is not None:
            self.link.close()
            self.link = None

    def send(self, command):
        """Write one command line. Silently does nothing if there's no link."""
        if self.link is None:
            return

        try:
            self.link.write((command + "\n").encode())
        except serial.SerialException as e:
            # Unplugged mid-conversation — drop the link and keep talking.
            self.log(f"[face] lost connection: {e}")
            self.close()

    def mode(self, name):
        self.send(f"mode {name}")

    def state(self, name):
        self.send(f"face {name}")

    def gesture(self, name):
        self.send(f"face {name}")

    def mood(self, name):
        """Colour the current state. "auto" hands control back to the state."""
        self.send(f"mood {name}")

    def __enter__(self):
        return self.connect()

    def __exit__(self, *exc):
        # Leave the bot idling rather than frozen on whatever it was last doing.
        self.state("idle")
        self.close()
        return False


if __name__ == "__main__":
    # Walk through every expression so you can eyeball them on the display.
    states = ["idle", "listening", "thinking", "speaking", "happy", "angry", "tired"]

    with RobotFace() as face:
        face.mode("face")

        for state in states:
            print(f"state: {state}")
            face.state(state)
            time.sleep(3)

        for gesture in ["laugh", "confused"]:
            print(f"gesture: {gesture}")
            face.gesture(gesture)
            time.sleep(3)
