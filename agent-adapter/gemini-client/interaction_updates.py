"""
Fetch and render a Gemini Interaction after a client notify.
"""

from __future__ import annotations

from typing import Any

from google import genai


def fetch_interaction(
        client: genai.Client,
        interaction_id: str,
        *,
        include_input: bool = True,
) -> Any:
    return client.interactions.get(
        interaction_id,
        include_input=include_input,
    )


def format_interaction(interaction: Any) -> str | None:
    """Extract printable assistant text from an Interaction."""
    text = getattr(interaction, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    # Fallback: walk steps for model_output content.
    parts: list[str] = []
    for step in getattr(interaction, "steps", None) or []:
        step_type = getattr(step, "type", None)
        if step_type not in {"model_output", "text"}:
            continue
        content = getattr(step, "content", None)
        chunk = _content_text(content)
        if chunk:
            parts.append(chunk)

    joined = "\n".join(parts).strip()
    return joined or None


def _content_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()

    parts: list[str] = []
    for block in content or []:
        if isinstance(block, str):
            if block.strip():
                parts.append(block.strip())
            continue
        if isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
            continue
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return "\n".join(parts).strip()
