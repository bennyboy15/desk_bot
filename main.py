from software import speechToText as s
from software import llm as claude

def main():

    # SPEECH-TO-TEXT
    text = s.transcribe_speech()
    
    # SEND TRANSCRIPTION TO CLAUDE
    if (len(text) > 0):
        claude.callClaude(text)
    else:
        print("No text was sent to claude")
    
    return True    

if __name__ == "__main__":
    main()
