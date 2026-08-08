#ifndef FACES_H
#define FACES_H

#include "Arduino.h"
#include "U8glib-HAL.h"

enum Mood
{
    NEUTRAL,
    HAPPY,
    SAD,
    WINK,
    THINK
};

extern U8GLIB_SH1106_128X64 u8g;
extern Mood mood;

void renderFace();
void doBlink();
void updateLookOffset();
void setMood(char c);
void setRandomMood();

#endif