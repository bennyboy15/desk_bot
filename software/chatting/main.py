import os
import sys

# robotFace lives one level up in software/, and these scripts are run directly
# rather than as a package, so the parent directory isn't on the path yet.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from speechToText import Listener
from speaker import Speaker
from llm import Conversation
from robotFace import RobotFace

# Said on its own, these end the session. Checked against the whole utterance so
# "goodbye" hangs up but "say goodbye to your dog for me" doesn't.
EXIT_PHRASES = {"goodbye", "bye", "stop", "exit", "quit", "shut down", "shutdown"}


def isExit(text):
    return text.strip().strip(".!?").lower() in EXIT_PHRASES


def main():
    with RobotFace() as face, Listener() as listener:
        face.mode("face")

        # Start neutral, then leave mood alone - it belongs to Claude from here.
        # Deliberately not reset per turn: a mood carries until Claude decides
        # the feeling has changed.
        face.mood("auto")

        # Opens the mic and measures the room once, up front, so no turn pays
        # for it. Everything after this starts recording immediately.
        listener.open()

        conversation = Conversation()

        while True:
            # LISTENING - eyes lean in and hold still while the mic is open
            face.state("listening")
            text = listener.listen()

            if not text:
                face.gesture("confused")
                continue

            if isExit(text):
                print("Goodbye!")
                break

            # THINKING - covers the wait for Claude's first words. Claude sets
            # its own mood during this call, which survives into speaking.
            face.state("thinking")

            # Speaker flips the face to "speaking" itself, once audio actually
            # starts, and each sentence is spoken as it arrives rather than
            # after the whole reply is written.
            speaker = Speaker(face)
            reply = conversation.ask(text, face, speaker.feed)
            speaker.finish()

            if not reply:
                face.gesture("confused")

    return True


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
