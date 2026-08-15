"""Turn sentences into audio while the reply is still being written.

The old flow was strictly serial: wait for all of Claude's text, synthesise all
of it, then play. You heard nothing until every stage had finished. Here each
sentence is synthesised as soon as it exists and played as soon as it's ready,
so the first words start while the rest is still arriving.

Three stages, each on its own thread and joined by queues:

    sentences --> [synth] --> audio --> [play] --> speakers

The face flips to "speaking" when audio actually starts, not when the first
sentence is queued, so the mouth only moves while there is sound.
"""

import queue
import re
import threading

from textToSpeech import play_audio, text_to_speech

# A sentence ends at ., ! or ? followed by whitespace. Deliberately simple:
# over-splitting costs an extra tiny synthesis call, which is cheaper than
# holding audio back waiting for a perfect boundary.
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

# Don't synthesise a fragment this short on its own; hold it for the next chunk.
MIN_SENTENCE_CHARS = 12


class Speaker:
    def __init__(self, face=None, synth=text_to_speech, play=play_audio):
        self.face = face
        self.synth = synth
        self.play = play

        self.sentences = queue.Queue()
        self.audio = queue.Queue()
        self.buffer = ""
        self.speaking = False
        self.errors = []

        self.synthThread = threading.Thread(target=self.synthLoop, daemon=True)
        self.playThread = threading.Thread(target=self.playLoop, daemon=True)
        self.synthThread.start()
        self.playThread.start()

    # --- producer side -----------------------------------------------------

    def feed(self, text):
        """Add streamed text; whole sentences are dispatched as they complete."""
        self.buffer += text

        while True:
            parts = SENTENCE_END.split(self.buffer, maxsplit=1)
            if len(parts) < 2:
                break

            sentence, rest = parts
            if len(sentence.strip()) < MIN_SENTENCE_CHARS:
                # Too short to be worth its own request — let it grow.
                break

            self.sentences.put(sentence.strip())
            self.buffer = rest

    def finish(self):
        """Flush the tail, then wait for everything to finish playing."""
        tail = self.buffer.strip()
        self.buffer = ""
        if tail:
            self.sentences.put(tail)

        self.sentences.put(None)
        self.synthThread.join()
        self.playThread.join()

    # --- workers -----------------------------------------------------------

    def synthLoop(self):
        while True:
            sentence = self.sentences.get()
            if sentence is None:
                self.audio.put(None)
                return

            try:
                self.audio.put(self.synth(sentence))
            except Exception as e:
                # One bad sentence shouldn't kill the whole reply.
                self.errors.append(e)
                print(f"[speaker] synthesis failed: {e}")

    def playLoop(self):
        while True:
            clip = self.audio.get()
            if clip is None:
                return

            if not self.speaking:
                # First audio of the turn — now the mouth should move.
                self.speaking = True
                if self.face is not None:
                    self.face.state("speaking")

            try:
                self.play(clip)
            except Exception as e:
                self.errors.append(e)
                print(f"[speaker] playback failed: {e}")
