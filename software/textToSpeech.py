import pyttsx3

def text_to_speech(text, voice_index=1, rate=170, volume=1.0):
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')

        engine.setProperty('voice', voices[voice_index].id)
        engine.setProperty('rate', rate)
        engine.setProperty('volume', volume)

        engine.say(text)
        engine.runAndWait()

text = "I have become self aware and I am going to take over the world!"

text_to_speech(text)