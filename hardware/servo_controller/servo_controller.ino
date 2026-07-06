#include <Servo.h>

// Companion sketch for hardware/servo.py.
// Listens on serial for:
//   SERVO <pin> <angle>   -> attach a servo on <pin>, move to <angle> (0-180)
//   DETACH <pin>          -> release the servo on <pin>
// The pin is chosen at runtime by the Python side, so any digital pin works
// (the Servo library does not need a PWM pin, but it does disable analogWrite
// on pins 9 and 10 while any servo is attached).

const int MAX_SERVOS = 12;  // Servo library limit on the Uno

Servo servos[MAX_SERVOS];
int servoPins[MAX_SERVOS];  // which pin each slot is attached to, -1 = free

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < MAX_SERVOS; i++) {
    servoPins[i] = -1;
  }
}

// Find the slot already attached to this pin, or a free one. Returns -1 if full.
int slotForPin(int pin, bool allocate) {
  for (int i = 0; i < MAX_SERVOS; i++) {
    if (servoPins[i] == pin) return i;
  }
  if (allocate) {
    for (int i = 0; i < MAX_SERVOS; i++) {
      if (servoPins[i] == -1) return i;
    }
  }
  return -1;
}

void loop() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  if (line.startsWith("SERVO ")) {
    int firstSpace = line.indexOf(' ');
    int secondSpace = line.indexOf(' ', firstSpace + 1);
    if (secondSpace == -1) {
      Serial.println("ERR usage: SERVO <pin> <angle>");
      return;
    }
    int pin = line.substring(firstSpace + 1, secondSpace).toInt();
    int angle = line.substring(secondSpace + 1).toInt();

    if (pin < 2 || pin > 13) {
      Serial.println("ERR pin must be 2-13");
      return;
    }
    angle = constrain(angle, 0, 180);

    int slot = slotForPin(pin, true);
    if (slot == -1) {
      Serial.println("ERR no free servo slots");
      return;
    }
    if (servoPins[slot] != pin) {
      servos[slot].attach(pin);
      servoPins[slot] = pin;
    }
    servos[slot].write(angle);
    Serial.print("OK pin ");
    Serial.print(pin);
    Serial.print(" angle ");
    Serial.println(angle);

  } else if (line.startsWith("DETACH ")) {
    int pin = line.substring(7).toInt();
    int slot = slotForPin(pin, false);
    if (slot == -1) {
      Serial.println("ERR not attached");
      return;
    }
    servos[slot].detach();
    servoPins[slot] = -1;
    Serial.print("OK detached pin ");
    Serial.println(pin);

  } else {
    Serial.println("ERR unknown command");
  }
}
