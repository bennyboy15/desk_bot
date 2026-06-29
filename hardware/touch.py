import os
import time
import serial
from serial.tools import list_ports
from dotenv import load_dotenv

load_dotenv()

# Serial config. Override the port in your .env (e.g. ARDUINO_PORT=COM3 on
# Windows, /dev/ttyACM0 on Linux). Baud must match Serial.begin() in the sketch.
PORT = os.getenv("ARDUINO_PORT")
BAUD = int(os.getenv("ARDUINO_BAUD", "9600"))

# What the Arduino prints over serial when the sensor is touched.
TOUCH_TOKEN = "TOUCHED"


def find_arduino_port():
    """Return the first serial port that looks like an Arduino, or None."""
    for p in list_ports.comports():
        text = f"{p.description} {p.manufacturer}".lower()
        if "arduino" in text or "ch340" in text or "usb serial" in text:
            return p.device
    return None


def open_serial(port=None, baud=BAUD, timeout=1.0):
    """Open the serial connection to the Arduino.

    Falls back to auto-detection if no port is configured. Gives the board a
    moment to reset (most Arduinos reboot when the port is opened).
    """
    port = port or PORT or find_arduino_port()
    if port is None:
        raise RuntimeError(
            "No Arduino serial port found. Set ARDUINO_PORT in your .env "
            "(e.g. COM3) or plug the board in."
        )

    ser = serial.Serial(port, baud, timeout=timeout)
    time.sleep(2)             # wait for the board to finish resetting
    ser.reset_input_buffer()  # drop any boot/garbage bytes
    print(f"Connected to Arduino on {port} @ {baud} baud")
    return ser


def is_touched(ser):
    """Read one line from serial and return True if it reports a touch.

    Respects the serial timeout, so it returns False if no line arrived in
    that window.
    """
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    if not line:
        return False
    return line.upper() == TOUCH_TOKEN


def wait_for_touch(ser):
    """Block until the sensor is touched. Returns True once it is."""
    print("Waiting for touch...")
    while True:
        if is_touched(ser):
            print("Touch detected!")
            return True


if __name__ == "__main__":
    ser = open_serial()
    try:
        while True:
            if is_touched(ser):
                print("Touch detected!")
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        ser.close()
