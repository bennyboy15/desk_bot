#include "U8glib-HAL.h"
#include "faces.h"
#include "walkingMan.h"
#include <Arduino.h>

U8GLIB_SH1106_128X64 u8g(13, 11, 10, 9, 8);

// How long each half of the cycle lasts: stats, then a random face
const unsigned long PHASE_DURATION = 30000;

char processorName[32] = "";
float cpuUsage = 0;
float ramUsage = 0;

uint8_t walkFrame = 0;
unsigned long lastFrameTime = 0;

bool showingStats = true;
unsigned long phaseStartTime = 0;

// Face animation timing, reset every time the face phase starts
unsigned long lastLookTime = 0;
unsigned long nextLookDelay = 2000;
unsigned long lastBlinkTime = 0;
unsigned long nextBlinkDelay = 3000;

void renderStats()
{
    u8g.firstPage();
    do
    {
        u8g.setFont(u8g_font_helvR08);
        u8g.drawStr(0, 15, ("PROCESSOR: " + String(processorName)).c_str());
        u8g.drawStr(0, 30, ("CPU: " + String(cpuUsage, 2) + "%").c_str());
        u8g.drawStr(0, 45, ("RAM: " + String(ramUsage, 2) + "%").c_str());
        drawWalkingMan(u8g, 92, 30, walkFrame);
    } while (u8g.nextPage());
}

void readSerial()
{
    if (!Serial.available())
    {
        return;
    }

    String data = Serial.readStringUntil('\n');
    char buf[64];
    data.toCharArray(buf, sizeof(buf));

    char *processor = strtok(buf, ",");
    char *cpu = strtok(NULL, ",");
    char *ram = strtok(NULL, ",");

    if (processor == NULL || cpu == NULL || ram == NULL)
    {
        return;
    }

    strncpy(processorName, processor, sizeof(processorName) - 1);
    processorName[sizeof(processorName) - 1] = '\0';
    cpuUsage = atof(cpu);
    ramUsage = atof(ram);
}

void runStatsPhase()
{
    if (millis() - lastFrameTime >= WALKING_MAN_FRAME_DELAY)
    {
        lastFrameTime = millis();
        walkFrame++;
        renderStats();
    }
}

void runFacePhase()
{
    unsigned long now = millis();

    if (mood != NEUTRAL)
    {
        renderFace();
        return;
    }

    if (now - lastLookTime > nextLookDelay)
    {
        updateLookOffset();
        lastLookTime = now;
        nextLookDelay = random(1500, 4000);
    }
    renderFace();
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

void startFacePhase()
{
    setRandomMood();
    unsigned long now = millis();
    lastLookTime = now;
    nextLookDelay = random(1500, 4000);
    lastBlinkTime = now;
    nextBlinkDelay = random(2000, 5000);
}

void setup()
{
    randomSeed(analogRead(A0));

    if (u8g.getMode() == U8G_MODE_BW)
    {
        u8g.setColorIndex(1); // pixel on
    }
    Serial.begin(9600);

    mood = NEUTRAL;
    phaseStartTime = millis();
}

void loop()
{
    readSerial();

    unsigned long now = millis();
    if (now - phaseStartTime >= PHASE_DURATION)
    {
        phaseStartTime = now;
        showingStats = !showingStats;
        if (!showingStats)
        {
            startFacePhase();
        }
    }

    if (showingStats)
    {
        runStatsPhase();
    }
    else
    {
        runFacePhase();
    }
}
