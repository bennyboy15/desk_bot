"""Serial link to the desk bot's face.

The firmware exposes two verbs (see hardware/src/main.cpp):
    mode <face|stats|next>   which screen is showing
    face <state|gesture>     what the eyes are doing

States are sticky (idle, listening, thinking, speaking, happy, angry, tired);
gestures are one-shot animations (laugh, confused) that play over whatever
state is current.

The link is optional on purpose: if the bot isn't plugged in, every call turns
into a no-op so a conversation still runs on the PC alone.

Two transports, tried in that order:
  1. robotDaemon's unix socket, if the daemon is running. Multiple programs can
     drive the bot at once this way.
  2. The serial port directly, which only one process can hold.
Both expose the same read/write surface, so nothing above here cares which.
"""

import os
import socket
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


SOCKET_PATH = os.environ.get(
    "DESKBOT_SOCKET", os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "deskbot.sock")
)


def findPort():
    """Return the bot's serial device, or None if it isn't connected."""
    for port in serial.tools.list_ports.comports():
        if (port.vid, port.pid) in ESP32_C3_IDS:
            return port.device
    return None


class SocketTransport:
    """Daemon socket dressed up as a serial port.

    Only the handful of methods RobotFace and its callers actually use, so a
    socket and a serial.Serial are interchangeable above this line.
    """

    def __init__(self, conn):
        self.conn = conn
        self.conn.setblocking(False)

    def write(self, data):
        self.conn.setblocking(True)
        try:
            self.conn.sendall(data)
        finally:
            self.conn.setblocking(False)

    def read_all(self):
        chunks = []
        while True:
            try:
                chunk = self.conn.recv(4096)
            except (BlockingIOError, InterruptedError):
                break
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)

    def reset_input_buffer(self):
        self.read_all()

    def close(self):
        self.conn.close()


class RobotFace:
    def __init__(self, port=None, quiet=False):
        self.port = port
        self.quiet = quiet
        self.link = None

    def log(self, message):
        if not self.quiet:
            print(message, file=sys.stderr)

    def connectDaemon(self):
        """Attach to robotDaemon if it's running. Cheap to try, so try first."""
        if self.port is not None:
            return False # an explicit port means "talk to the hardware directly"

        try:
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            conn.connect(SOCKET_PATH)
        except OSError:
            return False

        # No boot delay needed: the daemon already waited for the board.
        self.link = SocketTransport(conn)
        self.log(f"[face] connected via daemon at {SOCKET_PATH}")
        return True

    def connect(self):
        if self.connectDaemon():
            return self

        port = self.port or findPort()

        if port is None:
            self.log("[face] no bot found — carrying on without it")
            return self

        try:
            self.link = serial.Serial(port, BAUD, timeout=1)
        except serial.SerialException as e:
            # Usually the daemon, or another script, already holds the port.
            self.log(f"[face] could not open {port}: {e}")
            self.log("[face] if robotDaemon.py is running, clients reach it by socket")
            return self

        time.sleep(BOOT_DELAY)
        self.log(f"[face] connected directly on {port}")
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
        except (serial.SerialException, OSError) as e:
            # Unplugged, or the daemon went away — drop it and keep talking.
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
