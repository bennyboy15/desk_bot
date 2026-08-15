/*
  Mochi-style animated face — PlatformIO version
  Board:    ESP32-C3 Supermini
  Display:  Jaycar XC3728 / Keyestudio KS0056, 1.3" 128x64, SH1106 driver, SPI
  Library:  Adafruit_SH110X (for the SH1106 chip) + FluxGarage RoboEyes

  Wiring:
    OLED GND       -> ESP32-C3 GND
    OLED VCC       -> ESP32-C3 3V3
    OLED SCK/CLK   -> ESP32-C3 GPIO4
    OLED SDA/MOSI  -> ESP32-C3 GPIO6
    OLED RES/RST   -> ESP32-C3 GPIO10
    OLED DC        -> ESP32-C3 GPIO3
    OLED CS        -> ESP32-C3 GPIO7

  Serial protocol (115200 baud, newline-terminated):
    <name>,<cpu>,<ram>    PC stats, e.g. "Ryzen 7 5800X,42.5,63.1"
    mode face             switch to the animated face
    mode stats            switch to the PC stats readout
    mode next             cycle to the next mode
*/

#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <Arduino.h>
#include <FluxGarage_RoboEyes.h>
#include <SPI.h>
#include <strings.h>

// Echo every received line back over serial. Watch it with the PlatformIO
// monitor to confirm what the firmware is actually parsing.
#define DEBUG_SERIAL 1

// --- SPI pins ---
#define OLED_CLK 4  // SCK / CLK
#define OLED_MOSI 6 // SDA / MOSI
#define OLED_RES 10 // RES / RST
#define OLED_DC 3   // DC
#define OLED_CS 7   // CS

// --- OLED settings ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SH1106G display(SCREEN_WIDTH, SCREEN_HEIGHT, OLED_MOSI, OLED_CLK, OLED_DC, OLED_RES, OLED_CS);

RoboEyes<Adafruit_SH1106G> roboEyes(display);

// PC STATS + INFO
char processorName[32] = "";
float cpuUsage = 0;
float ramUsage = 0;
bool statsReceived = false;

// --- MODES ---
// To add a mode: add it to the enum before MODE_COUNT, write its enter/update
// functions, and add a case to each switch in enterMode() / updateMode().
enum Mode : uint8_t
{
    MODE_FACE,
    MODE_STATS,
    MODE_COUNT // keep last — used for cycling and bounds checks
};

Mode currentMode = MODE_FACE;

//*********************************************************************************************
//  FACE MODE
//*********************************************************************************************

void faceEnter()
{
    roboEyes.setMood(DEFAULT);
}

void faceUpdate()
{
    // RoboEyes owns the whole framebuffer: drawEyes() calls clearDisplay() at
    // the start and display() at the end, so nothing else may draw in this mode.
    roboEyes.update();

    static unsigned long lastChange = 0;
    static int state = 0;

    if (millis() - lastChange > 5000)
    {
        lastChange = millis();
        state = (state + 1) % 4;

        switch (state)
        {
        case 0:
            roboEyes.setMood(DEFAULT);
            break;
        case 1:
            roboEyes.setMood(HAPPY);
            break;
        case 2:
            roboEyes.setMood(TIRED);
            break;
        case 3:
            roboEyes.anim_laugh();
            break;
        }
    }
}

//*********************************************************************************************
//  STATS MODE
//*********************************************************************************************

// Full-width progress bar, 10px tall.
void drawBar(int16_t y, float percent)
{
    if (percent < 0)
    {
        percent = 0;
    }
    if (percent > 100)
    {
        percent = 100;
    }

    display.drawRect(0, y, SCREEN_WIDTH, 10, SH110X_WHITE);

    int16_t fill = (int16_t)((SCREEN_WIDTH - 4) * percent / 100.0f + 0.5f);
    if (fill > 0)
    {
        display.fillRect(2, y + 2, fill, 6, SH110X_WHITE);
    }
}

// Label on the left, right-aligned percentage on the right.
void drawStatLine(int16_t y, const char *label, float percent)
{
    char value[8];
    snprintf(value, sizeof(value), "%3.0f%%", percent);

    display.setCursor(0, y);
    display.print(label);

    // The default font advances 6px per character at size 1.
    display.setCursor(SCREEN_WIDTH - strlen(value) * 6, y);
    display.print(value);
}

void statsEnter()
{
    // Nothing to set up — statsUpdate() repaints the whole screen.
}

void statsUpdate()
{
    static unsigned long lastDraw = 0;
    if (millis() - lastDraw < 100) // 10 Hz is plenty for a stats readout
    {
        return;
    }
    lastDraw = millis();

    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SH110X_WHITE);
    display.setTextWrap(false); // a long CPU name must clip, not wrap into the bars

    if (!statsReceived)
    {
        const char *msg = "waiting for data...";
        display.setCursor((SCREEN_WIDTH - strlen(msg) * 6) / 2, 28);
        display.print(msg);
        display.display();
        return;
    }

    // Processor name across the top — centred if it fits, else left-aligned
    // and clipped at the right edge.
    int16_t x1, y1;
    uint16_t w, h;
    display.getTextBounds(processorName, 0, 0, &x1, &y1, &w, &h);
    display.setCursor(w < SCREEN_WIDTH ? (SCREEN_WIDTH - w) / 2 : 0, 0);
    display.print(processorName);

    display.drawFastHLine(0, 11, SCREEN_WIDTH, SH110X_WHITE);

    drawStatLine(16, "CPU", cpuUsage);
    drawBar(26, cpuUsage);

    drawStatLine(40, "RAM", ramUsage);
    drawBar(50, ramUsage);

    display.display();
}

//*********************************************************************************************
//  MODE DISPATCH
//*********************************************************************************************

void enterMode(Mode mode)
{
    currentMode = mode;

    // Every mode starts from a blank buffer so leftovers can't bleed through.
    display.clearDisplay();
    display.display();

    switch (mode)
    {
    case MODE_FACE:
        faceEnter();
        break;
    case MODE_STATS:
        statsEnter();
        break;
    default:
        break;
    }
}

void setMode(Mode mode)
{
    if (mode >= MODE_COUNT || mode == currentMode)
    {
        return;
    }
    enterMode(mode);
}

void nextMode()
{
    enterMode((Mode)((currentMode + 1) % MODE_COUNT));
}

void updateMode()
{
    switch (currentMode)
    {
    case MODE_FACE:
        faceUpdate();
        break;
    case MODE_STATS:
        statsUpdate();
        break;
    default:
        break;
    }
}

//*********************************************************************************************
//  SERIAL
//*********************************************************************************************

void parseStats(char *line)
{
    char *processor = strtok(line, ",");
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
    statsReceived = true;
}

void handleLine(char *line)
{
#if DEBUG_SERIAL
    Serial.printf("[rx] \"%s\"\n", line);
#endif

    if (strncasecmp(line, "mode ", 5) == 0)
    {
        const char *arg = line + 5;

        if (strcasecmp(arg, "face") == 0)
        {
            setMode(MODE_FACE);
        }
        else if (strcasecmp(arg, "stats") == 0)
        {
            setMode(MODE_STATS);
        }
        else if (strcasecmp(arg, "next") == 0)
        {
            nextMode();
        }
#if DEBUG_SERIAL
        else
        {
            Serial.printf("[!!] unknown mode \"%s\"\n", arg);
        }
        Serial.printf("[ok] mode is now %d\n", currentMode);
#endif
        return;
    }

    parseStats(line);
}

// Non-blocking: consumes whatever bytes have arrived and dispatches on newline.
// (readStringUntil() stalls the animation for up to its 1s timeout whenever a
// line arrives split across reads.)
// CR, LF and CRLF all terminate a line — terminals differ on which they send,
// and an empty line is ignored so CRLF doesn't dispatch twice.
void readSerial()
{
    static char buffer[80];
    static uint8_t length = 0;

    while (Serial.available())
    {
        char c = Serial.read();

        if (c == '\n' || c == '\r')
        {
            buffer[length] = '\0';
            if (length > 0)
            {
                handleLine(buffer);
            }
            length = 0;
            continue;
        }

        if (length < sizeof(buffer) - 1)
        {
            buffer[length++] = c;
        }
    }
}

//*********************************************************************************************
//  MAIN
//*********************************************************************************************

void setup()
{
    Serial.begin(115200);

    display.begin(0, true);
    display.clearDisplay();
    display.display();

    roboEyes.begin(SCREEN_WIDTH, SCREEN_HEIGHT, 100);
    roboEyes.setAutoblinker(ON, 3, 2);
    roboEyes.setIdleMode(ON, 2, 2);

    enterMode(MODE_FACE);
}

void loop()
{
    readSerial();
    updateMode();
}
