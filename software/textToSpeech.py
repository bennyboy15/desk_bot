import os
import subprocess
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def play_audio(audio_bytes):
    subprocess.run(
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-"],
        input=audio_bytes,
        check=True,
    )


instructions = "Voice Affect: Energetic and animated; dynamic with variations in pitch and tone. Tone: Excited and enthusiastic, conveying an upbeat and thrilling atmosphere. Pacing: Rapid delivery when describing the game or the key moments (e.g., an overtime thriller, pull off an unbelievable win to convey the intensity and build excitement. Slightly slower during dramatic pauses to let key points sink in. Emotion: Intensely focused, and excited. Giving off positive energy. Personality: Relatable and engaging. Pauses: Short, purposeful pauses after key moments in the game."
def text_to_speech(text):
    response = client.audio.speech.create(
        model="tts-1",
        voice="onyx",
        instructions=instructions,
        input=text
    )
    audio_content = response.read()
    return audio_content

text = "Hi there Maggie, how are you this fine evening"
response = text_to_speech(text)
play_audio(response)