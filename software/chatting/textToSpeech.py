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


# Timbre. Swap for another built-in voice: alloy, ash, ballad, coral, echo,
# fable, onyx, nova, sage, shimmer, verse, marin, cedar.
VOICE = "verse"

# Only gpt-4o-mini-tts honours `instructions` - tts-1 and tts-1-hd silently
# ignore it, which is why the old direction here never had any effect.
MODEL = "gpt-4o-mini-tts"

# A shade under natural pace. The unhurried delivery is most of the character.
SPEED = 1.2

instructions = (
    "Voice: a refined artificial intelligence assistant - a polished "
    "RP accent, male, measured and quietly authoritative.\n"
    "Tone: calm, courteous and unflappable. Never excited, never anxious. "
    "You have handled far stranger requests than this one.\n"
    "Pacing: unhurried and even, with clean pauses at commas and full stops. "
    "Let each sentence land rather than rushing into the next.\n"
    "Emotion: understated. Warmth comes through precision and attentiveness "
    "rather than enthusiasm. No exclamations, no sing-song, no upspeak.\n"
    "Diction: crisp consonants and fully pronounced word endings, but natural - "
    "precise, never clipped or mechanical.\n"
    "Personality: dry, subtly witty, faintly amused. Deliver understatement "
    "completely straight; the humour is in the restraint, so never lean on it."
)


def text_to_speech(text):
    response = client.audio.speech.create(
        model=MODEL,
        voice=VOICE,
        instructions=instructions,
        speed=SPEED,
        input=text,
    )
    audio_content = response.read()
    return audio_content