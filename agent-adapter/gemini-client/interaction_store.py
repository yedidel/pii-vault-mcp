"""
Persist the Gemini Interactions API interaction.id for this client.

Same role as openai-client/conversation_store.py.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from google import genai


DEFAULT_STORE_PATH = Path(
    os.getenv(
        "GEMINI_BRIDGE_INTERACTION_STORE",
        str(Path.home() / ".gemini-bridge" / "interaction.json"),
    )
)


def _read_store(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_store(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_interaction_id(path: Path | None = None) -> str | None:
    store_path = path or DEFAULT_STORE_PATH
    interaction_id = str(_read_store(store_path).get("interactionId") or "").strip()
    return interaction_id or None


def save_interaction_id(interaction_id: str, path: Path | None = None) -> None:
    store_path = path or DEFAULT_STORE_PATH
    interaction_id = interaction_id.strip()
    if not interaction_id:
        raise ValueError("interaction_id must be non-empty")
    payload = _read_store(store_path)
    payload["interactionId"] = interaction_id
    _write_store(store_path, payload)


def ensure_interaction_id(
        *,
        api_key: str,
        model: str,
        path: Path | None = None,
) -> str:
    existing = load_interaction_id(path)
    if existing:
        return existing

    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=model,
        input=(
            "Bridge continuation bootstrap for this Gemini client session. "
            "Acknowledge briefly that you are ready."
        ),
    )
    interaction_id = (interaction.id or "").strip()
    if not interaction_id:
        raise RuntimeError(
            "Gemini interactions.create() returned an empty interaction.id"
        )

    save_interaction_id(interaction_id, path)
    return interaction_id


def reset_interaction_id(path: Path | None = None) -> None:
    store_path = path or DEFAULT_STORE_PATH
    try:
        store_path.unlink()
    except OSError:
        pass
