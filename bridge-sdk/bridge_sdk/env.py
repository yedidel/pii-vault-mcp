"""Load Agent Adapter .env so ADAPTER_AUTH_TOKEN is available to the SDK."""

from __future__ import annotations

import os
from pathlib import Path


def _parse_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or os.getenv(key):
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def _candidate_env_paths() -> list[Path]:
    explicit = os.getenv("BRIDGE_SDK_ENV", "").strip()
    if explicit:
        return [Path(explicit)]

    candidates: list[Path] = []
    here = Path(__file__).resolve()
    # bridge-sdk/bridge_sdk/env.py -> repo root is parents[2]
    repo_root = here.parents[2]
    candidates.append(repo_root / "agent-adapter" / ".env")

    cwd = Path.cwd()
    candidates.append(cwd / "agent-adapter" / ".env")
    candidates.append(cwd / ".env")

    # de-dupe preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def load_adapter_env() -> Path | None:
    """
    Load agent-adapter/.env into os.environ (without overriding existing vars).

    Returns the path loaded, or None if no file was found.
    """
    for path in _candidate_env_paths():
        if path.is_file():
            _parse_env_file(path)
            return path
    return None
