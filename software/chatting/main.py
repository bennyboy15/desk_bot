from speechToText import transcribe_speech
from textToSpeech import text_to_speech, play_audio
from llm import callClaude

def main():

    # SPEECH-TO-TEXT
    text = transcribe_speech() or ""
    
    # SEND TRANSCRIPTION TO CLAUDE
    if (len(text) > 0):
        result = callClaude(text)
        audio = text_to_speech(result)
        play_audio(audio)
    else:
        print("No text was sent to...")
    
    return True    

if __name__ == "__main__":
    main()