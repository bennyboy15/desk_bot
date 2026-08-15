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
    face <state>          set the face: idle, listening, thinking, speaking,
                          happy, angry, tired
    face <gesture>        play a one-shot animation: laugh, confused
    mood <name>           colour the current state: neutral, tired, angry,
                          happy, or auto to let the state decide again
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

// Arduino.h defines DEFAULT as 1 (an ADC reference) and RoboEyes redefines it
// as 0 for its neutral mood and centred eye position — whichever header is
// included last wins. That's RoboEyes today only because the includes are
// sorted alphabetically. Pin the value we mean so a reorder can't turn a
// neutral face into TIRED, or centred eyes into a glance upward.
#define EYES_NEUTRAL 0

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
// NEED TO ADD A MODE = add it to the enum before MODE_COUNT, write its enter/update
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

// The face tracks what the robot is doing, driven from the PC over serial.
// The chat pipeline sends one state per stage of a conversation.
// NEED TO ADD A STATE = add it to the enum before EXPR_COUNT, add its name to
// expressionNames at the same index, and give it a case in applyExpression().
enum Expression : uint8_t
{
    EXPR_IDLE,
    EXPR_LISTENING,
    EXPR_THINKING,
    EXPR_SPEAKING,
    EXPR_HAPPY,
    EXPR_ANGRY,
    EXPR_TIRED,
    EXPR_COUNT // keep last — bounds the name lookup
};

// Indices must line up with the enum above.
const char *const expressionNames[EXPR_COUNT] = {
    "idle", "listening", "thinking", "speaking", "happy", "angry", "tired",
};

Expression currentExpression = EXPR_IDLE;

// --- MOUTH ---
// Only drawn while speaking. RoboEyes clears the whole framebuffer on every
// eye frame, so the mouth has to be painted on afterwards and pushed again.
#define MOUTH_WIDTH 44
#define MOUTH_CENTER_X (SCREEN_WIDTH / 2)
#define MOUTH_CENTER_Y 46 // sits below the raised eyes of the speaking face
#define MOUTH_CLOSED_HEIGHT 3
#define MOUTH_OPEN_HEIGHT 20
#define MOUTH_STEP_MS 80 // how often the mouth picks a new opening

int16_t mouthHeight = MOUTH_CLOSED_HEIGHT;
int16_t mouthTarget = MOUTH_CLOSED_HEIGHT;

// Random targets rather than a steady flap — a metronome reads as a machine,
// uneven motion reads as speech. Tweened with the same halving the eyes use.
void updateMouth()
{
    static unsigned long targetTimer = 0;

    if (millis() - targetTimer >= MOUTH_STEP_MS)
    {
        targetTimer = millis();
        mouthTarget = random(MOUTH_CLOSED_HEIGHT, MOUTH_OPEN_HEIGHT + 1);
    }

    mouthHeight = (mouthHeight + mouthTarget) / 2;
}

void drawMouth()
{
    // Wipe the full swept area first: the eyes redraw themselves each frame,
    // but a shrinking mouth would otherwise leave its old edges behind.
    display.fillRect(MOUTH_CENTER_X - MOUTH_WIDTH / 2, MOUTH_CENTER_Y - MOUTH_OPEN_HEIGHT / 2,
                     MOUTH_WIDTH, MOUTH_OPEN_HEIGHT, SH110X_BLACK);

    int16_t radius = mouthHeight / 2;
    if (radius > 6)
    {
        radius = 6;
    }

    display.fillRoundRect(MOUTH_CENTER_X - MOUTH_WIDTH / 2, MOUTH_CENTER_Y - mouthHeight / 2,
                          MOUTH_WIDTH, mouthHeight, radius, SH110X_WHITE);
}

// --- MOOD ---
// Mood is deliberately separate from state. The PC drives states to match what
// the robot is doing (listening, speaking); Claude drives mood to match what it
// is saying. Keeping them apart means a mood set while thinking survives the
// switch to speaking, instead of being overwritten by that state's own mood.
// Values are RoboEyes' mood constants; -1 means "no override, state decides".
#define MOOD_COUNT 4
int8_t moodOverride = -1;

// Indices are the RoboEyes mood values: DEFAULT 0, TIRED 1, ANGRY 2, HAPPY 3.
const char *const moodNames[MOOD_COUNT] = {
    "neutral", "tired", "angry", "happy",
};

// Every state starts from the same baseline, so settings can't leak between
// them — otherwise "speaking" would leave its flicker and its shrunken eyes
// behind. Geometry is reset here too, since RoboEyes' setters overwrite the
// defaults they tween back to.
void applyExpression(Expression expression)
{
    roboEyes.setVFlicker(OFF);
    roboEyes.setHFlicker(OFF);
    roboEyes.setCuriosity(OFF);
    roboEyes.setSweat(OFF);
    roboEyes.setPosition(EYES_NEUTRAL); // anything that is not a compass point centres the eyes
    roboEyes.setWidth(36, 36);
    roboEyes.setHeight(36, 36);
    roboEyes.setBorderradius(8, 8);
    roboEyes.setSpacebetween(10);

    // What this state would look like on its own; the override wins below.
    uint8_t stateMood = EYES_NEUTRAL;

    switch (expression)
    {
    case EXPR_IDLE:
        stateMood = EYES_NEUTRAL;
        roboEyes.setAutoblinker(ON, 3, 2);
        roboEyes.setIdleMode(ON, 2, 2);
        break;
    case EXPR_LISTENING:
        // Leans to the left edge and holds there — idle mode off so it doesn't
        // wander off the lean. Curiosity swells whichever eye is nearest the
        // edge, which sells it as leaning in rather than just looking sideways.
        stateMood = EYES_NEUTRAL;
        roboEyes.setAutoblinker(ON, 4, 2);
        roboEyes.setIdleMode(OFF);
        roboEyes.setCuriosity(ON);
        roboEyes.setBorderradius(12, 12); // softer, more open-looking
        roboEyes.setPosition(W);
        break;
    case EXPR_THINKING:
        // Frequent idle movement reads as looking around for an answer; the
        // sweat drop is the "working on it" cue.
        stateMood = TIRED;
        roboEyes.setAutoblinker(ON, 2, 1);
        roboEyes.setIdleMode(ON, 1, 1);
        roboEyes.setSweat(ON);
        roboEyes.setHeight(30, 30);
        break;
    case EXPR_SPEAKING:
        // Eyes shrink and move to the top of the screen to make room for the
        // mouth underneath, turning the display into an actual face.
        stateMood = HAPPY;
        roboEyes.setAutoblinker(ON, 3, 2);
        roboEyes.setIdleMode(OFF);
        roboEyes.setWidth(34, 34);
        roboEyes.setHeight(24, 24);
        roboEyes.setBorderradius(6, 6);
        roboEyes.setSpacebetween(12);
        roboEyes.setPosition(N);
        mouthHeight = MOUTH_CLOSED_HEIGHT;
        mouthTarget = MOUTH_CLOSED_HEIGHT;
        break;
    case EXPR_HAPPY:
        // Big and round.
        stateMood = HAPPY;
        roboEyes.setAutoblinker(ON, 3, 2);
        roboEyes.setIdleMode(ON, 2, 2);
        roboEyes.setWidth(38, 38);
        roboEyes.setHeight(38, 38);
        roboEyes.setBorderradius(14, 14);
        break;
    case EXPR_ANGRY:
        // Narrow, sharp-cornered, and trembling.
        stateMood = ANGRY;
        roboEyes.setAutoblinker(ON, 4, 2);
        roboEyes.setIdleMode(OFF);
        roboEyes.setHeight(30, 30);
        roboEyes.setBorderradius(3, 3);
        roboEyes.setSpacebetween(6);
        roboEyes.setHFlicker(ON, 1);
        break;
    case EXPR_TIRED:
        // Heavy-lidded: short eyes, slow blink, slow drift.
        stateMood = TIRED;
        roboEyes.setAutoblinker(ON, 2, 2);
        roboEyes.setIdleMode(ON, 3, 2);
        roboEyes.setHeight(24, 24);
        roboEyes.setBorderradius(10, 10);
        break;
    default:
        break;
    }

    // Claude's choice outranks the state's own idea of how it should look.
    roboEyes.setMood(moodOverride >= 0 ? (unsigned char)moodOverride : stateMood);

    currentExpression = expression;
}

// "auto" hands control back to whatever state is current. Re-applies straight
// away so the change shows without waiting for the next state transition.
bool setMood(const char *name)
{
    if (strcasecmp(name, "auto") == 0)
    {
        moodOverride = -1;
        applyExpression(currentExpression);
        return true;
    }

    for (uint8_t i = 0; i < MOOD_COUNT; i++)
    {
        if (strcasecmp(name, moodNames[i]) == 0)
        {
            moodOverride = (int8_t)i;
            applyExpression(currentExpression);
            return true;
        }
    }
    return false;
}

// Returns false if the name isn't a known state, so the caller can try gestures.
bool setExpression(const char *name)
{
    for (uint8_t i = 0; i < EXPR_COUNT; i++)
    {
        if (strcasecmp(name, expressionNames[i]) == 0)
        {
            applyExpression((Expression)i);
            return true;
        }
    }
    return false;
}

// One-shot animations. They play over whatever state is current and leave it
// alone, so a laugh mid-sentence doesn't knock the face out of "speaking".
bool playGesture(const char *name)
{
    if (strcasecmp(name, "laugh") == 0)
    {
        roboEyes.anim_laugh();
        return true;
    }
    if (strcasecmp(name, "confused") == 0)
    {
        roboEyes.anim_confused();
        return true;
    }
    return false;
}

void faceUpdate()
{
    // RoboEyes owns the framebuffer: drawEyes() clears it, draws the eyes, and
    // pushes. So the mouth has to go on straight afterwards and be pushed
    // again — and only on frames where the eyes actually redrew, or it would
    // be wiped mid-blink and flicker. update() bumps fpsTimer exactly when it
    // draws, which is the cheapest way to spot that.
    static unsigned long lastEyeFrame = 0;

    roboEyes.update();

    if (currentExpression == EXPR_SPEAKING && roboEyes.fpsTimer != lastEyeFrame)
    {
        lastEyeFrame = roboEyes.fpsTimer;
        updateMouth();
        drawMouth();
        display.display();
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
        // Re-apply rather than reset: a "face thinking" that arrived while the
        // stats screen was up should still be showing when we come back.
        applyExpression(currentExpression);
        break;
    case MODE_STATS:
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

#if DEBUG_SERIAL
// Print the framebuffer as ASCII art. Lets the rendering be checked over the
// serial monitor without having to eyeball the panel — the buffer is the exact
// thing the display was last given.
void dumpFrame()
{
    uint8_t *buffer = display.getBuffer();

    Serial.println("[frame]");
    for (int16_t y = 0; y < SCREEN_HEIGHT; y++)
    {
        char row[SCREEN_WIDTH + 1];
        for (int16_t x = 0; x < SCREEN_WIDTH; x++)
        {
            // Monochrome pages: bit (y & 7) of byte x + (y / 8) * width.
            row[x] = (buffer[x + (y / 8) * SCREEN_WIDTH] & (1 << (y & 7))) ? '#' : '.';
        }
        row[SCREEN_WIDTH] = '\0';
        Serial.println(row);
    }
    Serial.println("[/frame]");
}
#endif

void handleLine(char *line)
{
#if DEBUG_SERIAL
    Serial.printf("[rx] \"%s\"\n", line);

    if (strcasecmp(line, "dump") == 0)
    {
        dumpFrame();
        return;
    }
#endif

    if (strncasecmp(line, "mood ", 5) == 0)
    {
        const char *arg = line + 5;

        if (setMood(arg))
        {
#if DEBUG_SERIAL
            Serial.printf("[ok] mood is now %s\n", moodOverride < 0 ? "auto" : moodNames[moodOverride]);
#endif
        }
#if DEBUG_SERIAL
        else
        {
            Serial.printf("[!!] unknown mood \"%s\"\n", arg);
        }
#endif
        return;
    }

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

    if (strncasecmp(line, "face ", 5) == 0)
    {
        const char *arg = line + 5;

        // States are sticky, gestures are one-shot — try states first so a
        // name can't be both.
        if (setExpression(arg))
        {
#if DEBUG_SERIAL
            Serial.printf("[ok] face is now %s\n", expressionNames[currentExpression]);
#endif
        }
        else if (playGesture(arg))
        {
#if DEBUG_SERIAL
            Serial.printf("[ok] played gesture %s\n", arg);
#endif
        }
#if DEBUG_SERIAL
        else
        {
            Serial.printf("[!!] unknown face \"%s\"\n", arg);
        }
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

    // enterMode() applies the current expression, which sets the blinker and
    // idle timings — no need to configure them separately here.
    enterMode(MODE_FACE);
}

void loop()
{
    readSerial();
    updateMode();
}
