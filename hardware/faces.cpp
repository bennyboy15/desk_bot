#include "faces.h"

// Eye geometry
const int eyeWidth = 34;
const int eyeHeight = 40;
const int eyeRadius = 10;
const int eyeGap = 14;
const int centerY = 32;

// Base eye positions (left eye, right eye mirrors)
int baseLeftX = 64 - eyeGap / 2 - eyeWidth;
int baseRightX = 64 + eyeGap / 2;

// Current offsets for "look around" drift
int offsetX = 0;
int offsetY = 0;

// Current eye openness (height), shared with draw()
int currentHeight = eyeHeight;

// Blink timing
unsigned long lastBlinkTime = 0;
unsigned long nextBlinkDelay = 3000;

// Look-around timing
unsigned long lastLookTime = 0;
unsigned long nextLookDelay = 2000;

Mood mood = NEUTRAL;

void drawNeutralEye(int x)
{
    int y = centerY - currentHeight / 2 + offsetY;
    u8g.drawRBox(x + offsetX, y, eyeWidth, currentHeight, eyeRadius);
}

void drawHappyEye(int x)
{
    int cx = x + eyeWidth / 2;
    int r = eyeWidth / 2;
    u8g.drawDisc(cx, centerY, r);
    u8g.setColorIndex(0);
    u8g.drawDisc(cx, centerY + 12, r + 3);
    u8g.setColorIndex(1);
}

void drawSadEye(int x, bool isLeft)
{
    int y = centerY - eyeHeight / 2;
    u8g.drawRBox(x, y, eyeWidth, eyeHeight, eyeRadius);
    u8g.setColorIndex(0);
    if (isLeft)
    {
        u8g.drawTriangle(x - 1, y - 1,
                         x + eyeWidth + 1, y - 1,
                         x - 1, y + eyeHeight / 2);
    }
    else
    {
        u8g.drawTriangle(x - 1, y - 1,
                         x + eyeWidth + 1, y - 1,
                         x + eyeWidth + 1, y + eyeHeight / 2);
    }
    u8g.setColorIndex(1);
}

void drawClosedEye(int x)
{
    int h = 6;
    u8g.drawRBox(x, centerY - h / 2, eyeWidth, h, 3);
}

void drawThinkEye(int x)
{
    int h = eyeHeight / 2;
    u8g.drawRBox(x + 10, centerY - h - 4, eyeWidth, h, 6);
}

void draw(void)
{
    switch (mood)
    {
    case HAPPY:
        drawHappyEye(baseLeftX);
        drawHappyEye(baseRightX);
        break;
    case SAD:
        drawSadEye(baseLeftX, true);
        drawSadEye(baseRightX, false);
        break;
    case WINK:
        drawNeutralEye(baseLeftX);
        drawClosedEye(baseRightX);
        break;
    case THINK:
        drawThinkEye(baseLeftX);
        drawThinkEye(baseRightX);
        break;
    case NEUTRAL:
    default:
        drawNeutralEye(baseLeftX);
        drawNeutralEye(baseRightX);
        break;
    }
}

void render()
{
    u8g.firstPage();
    do
    {
        draw();
    } while (u8g.nextPage());
}

void doBlink()
{
    for (int h = eyeHeight; h >= 4; h -= 8)
    {
        currentHeight = h;
        render();
        delay(15);
    }
    delay(60);
    for (int h = 4; h <= eyeHeight; h += 8)
    {
        currentHeight = h;
        render();
        delay(15);
    }
    currentHeight = eyeHeight;
    render();
}

void updateLookOffset()
{
    offsetX = random(-6, 7);
    offsetY = random(-4, 5);
}

void setMood(char c)
{
    switch (c)
    {
    case 'h': mood = HAPPY; break;
    case 's': mood = SAD; break;
    case 'w': mood = WINK; break;
    case 't': mood = THINK; break;
    case 'n': mood = NEUTRAL; break;
    default:
        mood = NEUTRAL;
        return;
    }
    offsetX = 0;
    offsetY = 0;
    currentHeight = eyeHeight;
    Serial.print("mood: ");
    Serial.println(c);
}