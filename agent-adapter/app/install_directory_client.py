from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class PairStartResult:
    pairing_code: str
    qr_url: str
    expires_at: str


@dataclass(frozen=True)
class InstallLookup:
    user_install_id: str
    vault_service_url: str
    status: str


class InstallDirectoryClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def start_pairing(self) -> PairStartResult:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(f"{self._base_url}/api/pair/start")
            response.raise_for_status()
            body = response.json()
        return PairStartResult(
            pairing_code=str(body["pairingCode"]),
            qr_url=str(body["qrUrl"]),
            expires_at=str(body["expiresAt"]),
        )

    def get_pairing(self, pairing_code: str) -> dict[str, Any]:
        code = pairing_code.strip()
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self._base_url}/api/pair/{code}")
            response.raise_for_status()
            body = response.json()
        if not isinstance(body, dict):
            raise RuntimeError("invalid pairing response")
        return body

    def get_install(self, user_install_id: str) -> InstallLookup | None:
        install_id = user_install_id.strip()
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self._base_url}/api/installs/{install_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            body = response.json()
        if not isinstance(body, dict):
            raise RuntimeError("invalid install response")
        return InstallLookup(
            user_install_id=str(body["userInstallId"]),
            vault_service_url=str(body.get("vaultServiceUrl") or ""),
            status=str(body.get("status") or ""),
        )


def load_install_directory_client() -> InstallDirectoryClient | None:
    base_url = os.getenv("INSTALL_DIRECTORY_URL", "").strip()
    if not base_url:
        return None
    return InstallDirectoryClient(base_url)
