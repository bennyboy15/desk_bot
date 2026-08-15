"""Microphone input.

Calibration and opening the mic used to happen on every single turn, which cost
about a second of dead air each time. Listener does both once and keeps the
stream open, so later turns start recording immediately.
"""

import speech_recognition as sr


class Listener:
    def __init__(self, pauseThreshold=2.0, energyThreshold=300, calibrateSeconds=1.0):
        self.recognizer = sr.Recognizer()

        # How long a silence has to run before it counts as you being finished.
        self.recognizer.pause_threshold = pauseThreshold

        # How loud audio must be to count as speech rather than room noise.
        self.recognizer.energy_threshold = energyThreshold
        self.recognizer.dynamic_energy_threshold = False

        self.calibrateSeconds = calibrateSeconds
        self.microphone = None
        self.source = None

    def open(self):
        """Open the mic and measure the room. Costs about a second, once."""
        if self.source is not None:
            return self

        self.microphone = sr.Microphone()
        self.source = self.microphone.__enter__()

        print("Adjusting for ambient noise...")
        self.recognizer.adjust_for_ambient_noise(self.source, duration=self.calibrateSeconds)
        return self

    def close(self):
        if self.source is not None:
            self.microphone.__exit__(None, None, None)
            self.microphone = None
            self.source = None

    def listen(self, timeout=10, phraseTimeLimit=15):
        """Record one phrase and transcribe it. None if nothing usable arrived."""
        self.open()
        print("Listening... Speak now!")

        try:
            audio = self.recognizer.listen(
                self.source, timeout=timeout, phrase_time_limit=phraseTimeLimit
            )
            print("Processing audio...")
            text = self.recognizer.recognize_google(audio)
            print(f"Transcription: {text}")
            return text
        except sr.WaitTimeoutError:
            print("Listening timed out. No speech detected.")
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand the audio.")
        except sr.RequestError as e:
            print(f"Could not request results; {e}")

        return None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()
        return False


def transcribe_speech():
    """One-shot transcription. Pays calibration every call - prefer Listener."""
    with Listener() as listener:
        return listener.listen()


if __name__ == "__main__":
    transcribe_speech()
