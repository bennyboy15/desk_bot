import speech_recognition as sr

def transcribe_speech():
    recognizer = sr.Recognizer()

    # How long it waits until it thinks you have stopped talking
    recognizer.pause_threshold = 2.0  

    # How loud noise has to be to be considered talking (cater for ambient noise)
    recognizer.energy_threshold = 300  

    with sr.Microphone() as source:
        print("Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        recognizer.dynamic_energy_threshold = False 
        
        print("Listening... Speak now!")
        
        try:
            # phrase_time_limit = max limit of convo
            audio_data = recognizer.listen(source, timeout=10, phrase_time_limit=15)
            print("Processing audio...")
            
            text = recognizer.recognize_google(audio_data)
            print(f"Transcription: {text}")
            
        except sr.WaitTimeoutError:
            print("Listening timed out. No speech detected.")
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand the audio.")
        except sr.RequestError as e:
            print(f"Could not request results; {e}")

if __name__ == "__main__":
    transcribe_speech()
