import anthropic
from anthropic import beta_tool
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

SYSTEM_PROMPT = (
    "You are a helpful australian desk robot assistant. "
    "Keep replies short and conversational since they are spoken aloud.\n\n"
    "You have a physical face on an OLED screen. Use set_mood to match the "
    "feeling of what you are about to say, and play_gesture for a reaction in "
    "the moment. Set a mood when the feeling genuinely changes - not on every "
    "reply, and don't mention the face out loud. Whatever mood you set stays "
    "until you change it, including while you speak."
)

# Set for the duration of a callClaude() call. The tools reach the robot through
# this rather than taking it as a parameter, because the SDK calls them itself
# and only passes through what Claude put in the tool input.
_face = None

MOODS = ["neutral", "happy", "tired", "angry"]
GESTURES = ["laugh", "confused"]


@beta_tool
def set_mood(mood: str) -> str:
    """Set the robot's facial expression to match the tone of your reply.

    The mood persists across everything the robot does until changed again, so
    set it before speaking rather than after.

    Args:
        mood: One of "neutral", "happy", "tired", or "angry".
    """
    if mood not in MOODS:
        return f"Unknown mood {mood!r}. Valid moods: {', '.join(MOODS)}."

    if _face is not None:
        _face.mood(mood)

    return f"Face set to {mood}."


@beta_tool
def play_gesture(gesture: str) -> str:
    """Play a one-shot animation on the robot's face.

    Use for a brief reaction. It plays over the current mood without changing
    it: "laugh" shakes the eyes up and down, "confused" shakes them side to
    side.

    Args:
        gesture: One of "laugh" or "confused".
    """
    if gesture not in GESTURES:
        return f"Unknown gesture {gesture!r}. Valid gestures: {', '.join(GESTURES)}."

    if _face is not None:
        _face.gesture(gesture)

    return f"Played {gesture}."


def callClaude(msg: str, face=None) -> str:
    """Send a user message to Claude and return the text reply.

    Claude may drive the robot's face while composing the reply; pass the
    RobotFace to let it. Without one the tools still work, they just don't
    reach any hardware.
    """
    global _face
    _face = face

    try:
        # tool_runner handles the call/execute/loop cycle, so a mood change
        # followed by the actual reply is one call from here.
        runner = client.beta.messages.tool_runner(
            model="claude-opus-4-8",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[set_mood, play_gesture],
            messages=[
                {
                    "role": "user",
                    "content": msg,
                }
            ],
        )

        final = None
        for message in runner:
            final = message
    except anthropic.APIError as e:
        print(f"Claude API error: {e}")
        return ""
    finally:
        _face = None

    if final is None:
        return ""

    reply = "".join(block.text for block in final.content if block.type == "text")
    print(reply)
    return reply
