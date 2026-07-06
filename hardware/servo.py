import argparse
import time

# Reuses the serial setup from touch.py (same folder). Works when run as
# "python hardware/servo.py" because Python adds the script's dir to the path.
from touch import open_serial

# Command format sent to the Arduino sketch (servo_controller.ino):
#   SERVO <pin> <angle>\n   -> attach servo on <pin> and move to <angle>
#   DETACH <pin>\n          -> release the servo on <pin>
# The sketch replies "OK ..." or "ERR ...".


def send_command(ser, command):
    """Send one command line and print the Arduino's reply."""
    ser.write(f"{command}\n".encode("utf-8"))
    reply = ser.readline().decode("utf-8", errors="ignore").strip()
    if reply:
        print(f"Arduino: {reply}")
    return reply


def set_angle(ser, pin, angle):
    """Move the servo on the given pin to an angle (0-180 degrees)."""
    if not 0 <= angle <= 180:
        raise ValueError("Angle must be between 0 and 180")
    return send_command(ser, f"SERVO {pin} {angle}")


def detach(ser, pin):
    """Release the servo so it stops holding position (and stops jittering)."""
    return send_command(ser, f"DETACH {pin}")


def sweep(ser, pin, start=0, end=180, step=10, delay=0.15):
    """Sweep the servo back and forth once between start and end."""
    for angle in range(start, end + 1, step):
        set_angle(ser, pin, angle)
        time.sleep(delay)
    for angle in range(end, start - 1, -step):
        set_angle(ser, pin, angle)
        time.sleep(delay)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Control a servo on an Arduino Uno")
    parser.add_argument("--pin", type=int, required=True,
                        help="Digital pin the servo signal wire is on (e.g. 9)")
    parser.add_argument("--angle", type=int,
                        help="Move to this angle (0-180) and exit")
    parser.add_argument("--sweep", action="store_true",
                        help="Do one 0-180-0 sweep and exit")
    args = parser.parse_args()

    ser = open_serial()
    try:
        if args.sweep:
            sweep(ser, args.pin)
        elif args.angle is not None:
            set_angle(ser, args.pin, args.angle)
        else:
            # Interactive mode: type an angle, or "q" to quit.
            print(f"Controlling servo on pin {args.pin}. "
                  "Enter an angle 0-180, or q to quit.")
            while True:
                entry = input("> ").strip().lower()
                if entry in ("q", "quit", "exit"):
                    break
                try:
                    set_angle(ser, args.pin, int(entry))
                except ValueError as e:
                    print(f"Invalid input: {e}")
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        detach(ser, args.pin)
        ser.close()
