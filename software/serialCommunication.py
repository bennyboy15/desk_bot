import serial
import time
import keyboard

arduino = serial.Serial('COM6', 115200, timeout=1)
#arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1) LINUX
time.sleep(2)  # Uno resets on serial connect — wait for it to boot

validKeys = ['h', 's', 'w', 't']

def handleKeyboardInput():
    event = keyboard.read_event()
    if event.event_type == keyboard.KEY_DOWN:
        pressedKey = event.name
        print(f"Key pressed: {pressedKey}")
        if pressedKey in validKeys:
            print(f"Valid key pressed: {pressedKey}")
            arduino.write(pressedKey.encode())
            time.sleep(3)
            arduino.write(b'n')

def send(cmd):
    arduino.write((cmd + "\n").encode())

while True:
    print("MODE STATS")
    send("mode stats")
    time.sleep(5)
    print("MODE FACE")
    send("mode face")
    time.sleep(5)

