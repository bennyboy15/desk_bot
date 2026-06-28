import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

SYSTEM_PROMPT = (
    "You are a helpful desk robot assistant. "
    "Keep replies short and conversational since they are spoken aloud."
)


def callClaude(msg: str) -> str:
    """Send a user message to Claude and return the text reply."""
    try:
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": msg,
                }
            ],
        )
    except anthropic.APIError as e:
        print(f"Claude API error: {e}")
        return ""

    reply = "".join(block.text for block in message.content if block.type == "text")
    print(reply)
    return reply
