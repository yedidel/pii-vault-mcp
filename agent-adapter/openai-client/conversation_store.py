"""
Persist the OpenAI Conversations API conversation.id for this client.

The Adapter never creates this id. The client bootstraps it once and reuses it
so Bridge → OpenAIProvider wakes land in the same conversation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI

DEFAULT_STORE_PATH = Path(
    os.getenv(
        "OPENAI_BRIDGE_CONVERSATION_STORE",
        Path.home() / ".openai-bridge" / "conversation.json",
    )
)


def _read_store(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError):
        return {}

    if not isinstance(payload, dict):
        return {}
    return payload


def _write_store(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    temp_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def load_conversation_id(path: Path | None = None) -> str | None:
    store_path = path or DEFAULT_STORE_PATH
    conversation_id = str(_read_store(store_path).get("conversationId") or "").strip()
    return conversation_id or None


def save_conversation_id(conversation_id: str, path: Path | None = None) -> None:
    store_path = path or DEFAULT_STORE_PATH
    conversation_id = conversation_id.strip()
    if not conversation_id:
        raise ValueError("conversation_id must be non-empty")

    payload = _read_store(store_path)
    payload["conversationId"] = conversation_id
    _write_store(store_path, payload)


def ensure_conversation_id(
        *,
        api_key: str | None = None,
        path: Path | None = None,
) -> str:
    """
    Return a durable conversation.id, creating one only when none is stored.
    """
    existing = load_conversation_id(path)
    if existing:
        return existing

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Missing OPENAI_API_KEY in environment")

    client = OpenAI(api_key=key)
    conversation = client.conversations.create()
    conversation_id = (conversation.id or "").strip()
    if not conversation_id:
        raise RuntimeError(
            "OpenAI conversations.create() returned an empty conversation.id"
        )

    save_conversation_id(conversation_id, path)
    return conversation_id


def reset_conversation_id(path: Path | None = None) -> None:
    store_path = path or DEFAULT_STORE_PATH
    if store_path.exists():
        store_path.unlink()
