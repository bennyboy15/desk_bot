#include "U8glib.h"
#include "faces.h"

U8GLIB_SH1106_128X64 u8g(13, 11, 10, 9); // SCK, MOSI, CS, DC(A0)

void setup(void)
{
    randomSeed(analogRead(A0));

    if (u8g.getMode() == U8G_MODE_BW)
    {
        u8g.setColorIndex(1); // pixel on
    }

    Serial.begin(9600);
    mood = NEUTRAL;
}

void loop(void)
{
    if (Serial.available() > 0)
    {
        char c = Serial.read();
        setMood(tolower(c));
    }

    unsigned long now = millis();

    if (mood == NEUTRAL)
    {
        static unsigned long lastLookTime = 0;
        static unsigned long nextLookDelay = 2000;
        static unsigned long lastBlinkTime = 0;
        static unsigned long nextBlinkDelay = 3000;

        if (now - lastLookTime > nextLookDelay)
        {
            updateLookOffset();
            lastLookTime = now;
            nextLookDelay = random(1500, 4000);
        }
        render();
        if (now - lastBlinkTime > nextBlinkDelay)
        {
            doBlink();
            if (random(0, 100) < 25)
            {
                delay(120);
                doBlink();
            }
            lastBlinkTime = now;
            nextBlinkDelay = random(2000, 5000);
        }
    }
    else
    {
        render();
    }
}