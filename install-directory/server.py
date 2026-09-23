#!/usr/bin/env python3
"""
Install Directory (mock) — maps user_install_id to vault_service_url.

Phase 1 (Option A): pairing via web page + QR-friendly URL.

API:
  POST /api/pair/start
  POST /api/pair/complete   { pairingCode, vaultServiceUrl? }
  GET  /api/installs/{user_install_id}
  GET  /pair?code=...       HTML pairing page

Run:
  python install-directory/server.py
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from directory_store import DirectoryStore

HOST = os.getenv("INSTALL_DIRECTORY_HOST", "127.0.0.1")
PORT = int(os.getenv("INSTALL_DIRECTORY_PORT", "8010"))
PUBLIC_BASE = os.getenv(
    "INSTALL_DIRECTORY_PUBLIC_BASE",
    f"http://{HOST}:{PORT}",
).rstrip("/")
DEFAULT_VAULT_SERVICE_URL = os.getenv(
    "DEFAULT_VAULT_SERVICE_URL",
    "ws://127.0.0.1:8081/vault-websocket",
).strip()

BASE_DIR = Path(__file__).resolve().parent
PAIR_HTML = (BASE_DIR / "pair.html").read_text(encoding="utf-8")
STORE = DirectoryStore(BASE_DIR / "data" / "directory.sqlite3")


class DirectoryHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        print(f"[install-directory] {self.address_string()} - {format % args}")

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/pair":
            return self._send_html(200, PAIR_HTML)

        if path.startswith("/api/installs/"):
            user_install_id = path.removeprefix("/api/installs/").strip()
            record = STORE.get_install(user_install_id)
            if record is None:
                return self._send_json(
                    404,
                    {
                        "status": "NOT_REGISTERED",
                        "userInstallId": user_install_id,
                    },
                )
            return self._send_json(
                200,
                {
                    "userInstallId": record.user_install_id,
                    "vaultServiceUrl": record.vault_service_url,
                    "status": record.status,
                    "createdAt": record.created_at.isoformat(),
                    "lastSeenAt": record.last_seen_at.isoformat(),
                },
            )

        if path.startswith("/api/pair/"):
            pairing_code = path.removeprefix("/api/pair/").strip()
            session = STORE.get_pairing(pairing_code)
            if session is None:
                return self._send_json(404, {"detail": "pairing_code not found"})
            now = STORE._now()
            expired = session.expires_at <= now
            payload = {
                "pairingCode": session.pairing_code,
                "status": session.status,
                "expiresAt": session.expires_at.isoformat(),
                "expired": expired,
            }
            if session.user_install_id:
                payload["userInstallId"] = session.user_install_id
            return self._send_json(200, payload)

        if path == "/health":
            return self._send_json(200, {"status": "ok"})

        self._send_json(404, {"detail": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        payload = self._read_json_body()
        if payload is None:
            return self._send_json(400, {"detail": "Invalid JSON body"})

        if path == "/api/pair/start":
            session = STORE.start_pairing()
            qr_url = f"{PUBLIC_BASE}/pair?code={session.pairing_code}"
            return self._send_json(
                200,
                {
                    "pairingCode": session.pairing_code,
                    "qrUrl": qr_url,
                    "expiresAt": session.expires_at.isoformat(),
                },
            )

        if path == "/api/pair/complete":
            pairing_code = str(
                payload.get("pairingCode") or payload.get("pairing_code") or "",
            ).strip()
            vault_url = str(
                payload.get("vaultServiceUrl")
                or payload.get("vault_service_url")
                or DEFAULT_VAULT_SERVICE_URL,
            ).strip()
            if not pairing_code:
                return self._send_json(
                    400,
                    {"detail": "pairingCode is required"},
                )
            try:
                record = STORE.complete_pairing(
                    pairing_code,
                    vault_service_url=vault_url,
                )
            except KeyError:
                return self._send_json(404, {"detail": "pairing_code not found"})
            except PermissionError as error:
                return self._send_json(410, {"detail": str(error)})
            except ValueError as error:
                return self._send_json(400, {"detail": str(error)})

            return self._send_json(
                200,
                {
                    "userInstallId": record.user_install_id,
                    "vaultServiceUrl": record.vault_service_url,
                    "status": record.status,
                },
            )

        self._send_json(404, {"detail": "Not found"})


def main() -> None:
    print(f"--- Install Directory on {PUBLIC_BASE} ---")
    print(f"--- Default vault URL: {DEFAULT_VAULT_SERVICE_URL} ---")
    print("--- Pairing page: /pair?code=... ---")
    server = HTTPServer((HOST, PORT), DirectoryHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
