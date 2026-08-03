"""Create one Gemini Interaction and print its id (for use as send_action sessionId)."""
import os

from google import genai

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise SystemExit("Set GEMINI_API_KEY or GOOGLE_API_KEY")

client = genai.Client(api_key=api_key)
interaction = client.interactions.create(
    model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
    input="You are a Bridge agent. Reply briefly that you are ready.",
)
print(interaction.id)
