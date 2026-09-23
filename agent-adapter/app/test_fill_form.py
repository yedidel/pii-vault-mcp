#!/usr/bin/env python3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from mcp_server import send_action

if __name__ == "__main__":
    result = send_action(
        agentId="agent-123",
        actionType="FILL_FORM",
        parameters={
            "name": "Dana",
            "email": "dana@example.com",
            "password": "Secret123",
        },
        sessionId="manual-fill-form-test",
        platform="gemini",
    )
    print(result)
