"""
Fetch and render new OpenAI Conversation items after a client notify.
"""

from __future__ import annotations

from typing import Any

from openai import OpenAI


def latest_conversation_item_id(
        client: OpenAI,
        conversation_id: str,
) -> str | None:
    page = client.conversations.items.list(
        conversation_id,
        limit=1,
        order="desc",
    )
    items = list(getattr(page, "data", None) or [])
    if not items:
        return None
    item_id = getattr(items[0], "id", None)
    return str(item_id).strip() if item_id else None


def fetch_new_conversation_items(
        client: OpenAI,
        conversation_id: str,
        after_item_id: str | None,
) -> tuple[list[Any], str | None]:
    """
    Return (new_items, new_cursor).

    Uses Conversations items list with after= cursor so only deltas
    since the last seen item are returned.
    """
    kwargs: dict[str, Any] = {
        "limit": 100,
        "order": "asc",
    }
    if after_item_id:
        kwargs["after"] = after_item_id

    page = client.conversations.items.list(conversation_id, **kwargs)
    items = list(getattr(page, "data", None) or [])
    if not items:
        return [], after_item_id

    new_cursor = getattr(items[-1], "id", None) or after_item_id
    new_cursor = str(new_cursor).strip() if new_cursor else after_item_id
    return items, new_cursor


def format_conversation_item(item: Any) -> str | None:
    """Extract printable text from a Conversation item, if any."""
    item_type = getattr(item, "type", None)

    if item_type == "message":
        role = getattr(item, "role", None) or "message"
        text = _content_text(getattr(item, "content", None))
        if not text:
            return None
        return f"{role}> {text}"

    # Some SDKs expose output_text on message-like objects.
    text = getattr(item, "output_text", None)
    if isinstance(text, str) and text.strip():
        return f"assistant> {text.strip()}"

    return None


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
