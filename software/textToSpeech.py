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

def text_to_speech(text):
    response = client.audio.speech.create(
        model="tts-1",
        voice="shimmer",
        input=text
    )
    audio_content = response.read()
    return audio_content

text = "Hi there Maggie, how are you this fine evening"
response = text_to_speech(text)
play_audio(response)