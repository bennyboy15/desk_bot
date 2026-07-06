import serial
import time

arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(2)  # Uno resets on serial connect — wait for it to boot

arduino.write(b'h')
time.sleep(3)
arduino.write(b's')
time.sleep(3)
arduino.write(b'w')
time.sleep(3)
arduino.write(b't')
time.sleep(3)
arduino.write(b'n')
