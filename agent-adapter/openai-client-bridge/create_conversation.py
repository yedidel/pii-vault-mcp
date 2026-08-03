#!/usr/bin/env python3
"""
OpenAI client bootstrap for Bridge continuation.

Creates a durable Conversations API conversation and prints conversation.id.
Pass that id as sessionId when calling send_action with platform=openai.

This client is independent of the Adapter (same role as Claude bridge-wake
and Gemini hooks). The Adapter only stores and later wakes on the id.

Usage:
  OPENAI_API_KEY=... python create_conversation.py
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY in environment", file=sys.stderr)
        return 1

    try:
        from openai import OpenAI
    except ImportError:
        print(
            "Missing openai package. Install with: pip install openai",
            file=sys.stderr,
        )
        return 1

    client = OpenAI(api_key=api_key)
    conversation = client.conversations.create()
    conversation_id = (conversation.id or "").strip()

    if not conversation_id:
        print(
            "OpenAI conversations.create() returned an empty conversation.id",
            file=sys.stderr,
        )
        return 1

    print(conversation_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
