"""Single owner of the bot's serial port.

Only one process can hold /dev/ttyACM0, so the stats feed and the chat pipeline
could never run at the same time. This daemon takes the port and lets any
number of clients talk to the bot over a unix socket instead.

    python software/robotDaemon.py

It also runs the stats feed itself, so the stats screen stays live no matter
what else is connected. Clients speak the firmware's own line protocol, and
everything the firmware says back is broadcast to all of them.

RobotFace finds this automatically — nothing else needs to change.
"""

import os
import signal
import socket
import sys
import threading
import time

import serial

from hardwareInfo import primeCpuPercent, shortCpuName, statsLine
from robotFace import BAUD, BOOT_DELAY, findPort

# Somewhere both the daemon and its clients can agree on without configuration.
SOCKET_PATH = os.environ.get(
    "DESKBOT_SOCKET", os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "deskbot.sock")
)

STATS_INTERVAL = 1.0
RECONNECT_DELAY = 2.0


class RobotDaemon:
    def __init__(self, socketPath=SOCKET_PATH, port=None, stats=True):
        self.socketPath = socketPath
        self.port = port
        self.stats = stats

        self.link = None
        self.linkLock = threading.Lock()  # guards writes and reconnects
        self.clients = []
        self.clientLock = threading.Lock()
        self.running = True

    # --- serial ------------------------------------------------------------

    def connectSerial(self):
        port = self.port or findPort()
        if port is None:
            return False

        try:
            self.link = serial.Serial(port, BAUD, timeout=0.2)
        except serial.SerialException as e:
            print(f"[daemon] cannot open {port}: {e}", file=sys.stderr)
            return False

        time.sleep(BOOT_DELAY)
        print(f"[daemon] serial on {port}", file=sys.stderr)
        return True

    def write(self, line):
        with self.linkLock:
            if self.link is None:
                return
            try:
                self.link.write((line + "\n").encode())
            except serial.SerialException as e:
                print(f"[daemon] serial write failed: {e}", file=sys.stderr)
                self.dropSerial()

    def dropSerial(self):
        """Caller must hold linkLock."""
        if self.link is not None:
            try:
                self.link.close()
            except Exception:
                pass
            self.link = None

    def serialReader(self):
        """Pump firmware output out to every client, and reconnect if unplugged."""
        while self.running:
            if self.link is None:
                if not self.connectSerial():
                    time.sleep(RECONNECT_DELAY)
                continue

            try:
                data = self.link.read_all()
            except serial.SerialException as e:
                print(f"[daemon] serial read failed: {e}", file=sys.stderr)
                with self.linkLock:
                    self.dropSerial()
                continue

            if data:
                self.broadcast(data)
            else:
                time.sleep(0.02)

    # --- clients -----------------------------------------------------------

    def broadcast(self, data):
        with self.clientLock:
            dead = []
            for conn in self.clients:
                try:
                    conn.sendall(data)
                except OSError:
                    dead.append(conn)
            for conn in dead:
                self.clients.remove(conn)

    def serveClient(self, conn):
        with self.clientLock:
            self.clients.append(conn)

        buffer = b""
        try:
            while self.running:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                # Clients send the firmware's own newline-delimited protocol.
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.decode(errors="replace").strip()
                    if line:
                        self.write(line)
        except OSError:
            pass
        finally:
            with self.clientLock:
                if conn in self.clients:
                    self.clients.remove(conn)
            conn.close()

    # --- stats -------------------------------------------------------------

    def statsFeed(self):
        # get_cpu_info() spawns a subprocess, so read the name once up front.
        processorName = shortCpuName()
        primeCpuPercent()

        while self.running:
            self.write(statsLine(processorName))
            time.sleep(STATS_INTERVAL)

    # --- lifecycle ---------------------------------------------------------

    def run(self):
        # A socket left behind by a crash would block bind().
        if os.path.exists(self.socketPath):
            os.unlink(self.socketPath)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.socketPath)
        server.listen(8)
        print(f"[daemon] listening on {self.socketPath}", file=sys.stderr)

        # systemd, pkill and friends send SIGTERM, which wouldn't otherwise run
        # the cleanup below and would leave a stale socket file behind. Raising
        # KeyboardInterrupt routes it through the same shutdown path as Ctrl-C.
        def onTerm(signum, frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, onTerm)

        threading.Thread(target=self.serialReader, daemon=True).start()
        if self.stats:
            threading.Thread(target=self.statsFeed, daemon=True).start()

        try:
            while self.running:
                conn, _ = server.accept()
                threading.Thread(target=self.serveClient, args=(conn,), daemon=True).start()
        except KeyboardInterrupt:
            print("\n[daemon] shutting down", file=sys.stderr)
        finally:
            self.running = False
            server.close()
            if os.path.exists(self.socketPath):
                os.unlink(self.socketPath)
            with self.linkLock:
                self.dropSerial()


if __name__ == "__main__":
    RobotDaemon(stats="--no-stats" not in sys.argv).run()
