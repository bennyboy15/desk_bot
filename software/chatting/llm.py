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


class Conversation:
    """A running conversation. Keeps history so the bot remembers the thread."""

    def __init__(self, model="claude-opus-4-8", maxTokens=1024):
        self.model = model
        self.maxTokens = maxTokens
        self.messages = []

    def ask(self, msg: str, face=None, onText=None) -> str:
        """Send a message and return the reply.

        onText, if given, is called with each chunk of text as it streams in —
        that's what lets speech start before the reply has finished arriving.
        Claude may drive the face during the call; pass the RobotFace to allow it.
        """
        global _face
        _face = face

        self.messages.append({"role": "user", "content": msg})
        reply = ""

        try:
            # Streaming so text can be spoken as it arrives; tool_runner still
            # handles the call/execute/loop cycle around it.
            runner = client.beta.messages.tool_runner(
                model=self.model,
                max_tokens=self.maxTokens,
                system=SYSTEM_PROMPT,
                tools=[set_mood, play_gesture],
                messages=self.messages,
                stream=True,
            )

            # Each iteration is one assistant turn: text, or a tool call the
            # runner resolves before looping again.
            for stream in runner:
                for event in stream:
                    if event.type != "content_block_delta":
                        continue
                    if event.delta.type != "text_delta":
                        continue

                    reply += event.delta.text
                    if onText is not None:
                        onText(event.delta.text)
        except anthropic.APIError as e:
            print(f"Claude API error: {e}")
            # Drop the unanswered turn so the next question isn't sent with a
            # dangling user message and no reply.
            self.messages.pop()
            return ""
        finally:
            _face = None

        # Store just the text. The tool calls were resolved inside the runner,
        # and keeping their blocks here risks a tool_use with no tool_result.
        self.messages.append({"role": "assistant", "content": reply})
        return reply


def callClaude(msg: str, face=None) -> str:
    """Single-exchange helper, kept for scripts that don't want history."""
    return Conversation().ask(msg, face)
