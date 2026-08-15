import os
import sys

# robotFace lives one level up in software/, and these scripts are run directly
# rather than as a package, so the parent directory isn't on the path yet.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from speechToText import transcribe_speech
from textToSpeech import text_to_speech, play_audio
from llm import callClaude
from robotFace import RobotFace

def main():

    with RobotFace() as face:
        face.mode("face")

        # LISTENING - eyes hold still and attentive while the mic is open
        face.state("listening")
        text = transcribe_speech() or ""

        if (len(text) == 0):
            print("No text was sent to Claude")
            face.gesture("confused")
            return False

        # THINKING - covers the Claude call and the speech synthesis, since
        # both happen before there is anything to play
        face.state("thinking")
        result = callClaude(text)

        if (len(result) == 0):
            print("Claude returned nothing")
            face.gesture("confused")
            return False

        audio = text_to_speech(result)

        # SPEAKING - set immediately before playback so the eyes bob in time
        # with the voice; play_audio blocks until the clip finishes
        face.state("speaking")
        play_audio(audio)

    # Leaving the block drops the face back to idle.
    return True

if __name__ == "__main__":
    main()
