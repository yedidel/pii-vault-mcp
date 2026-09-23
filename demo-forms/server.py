#!/usr/bin/env python3
"""
Demo registration form server for FILL_FORM workflows.

Serves:
  GET  /register       HTML form (also GET /)
  POST /api/register   JSON body {name, email, password}
  GET  /api/registrations  list of submissions (passwords omitted)
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = os.getenv("DEMO_FORMS_HOST", "127.0.0.1")
PORT = int(os.getenv("DEMO_FORMS_PORT", "9000"))
BASE_DIR = Path(__file__).resolve().parent
REGISTER_HTML = (BASE_DIR / "register.html").read_text(encoding="utf-8")

REGISTRATIONS: list[dict[str, str]] = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class DemoFormsHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        print(f"[demo-forms] {self.address_string()} - {format % args}")

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        parsed = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(parsed, dict):
            raise ValueError("JSON body must be an object")
        return parsed

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/register"}:
            self._send_html(REGISTER_HTML)
            return
        if path == "/api/registrations":
            public = [
                {
                    "registrationId": item["registrationId"],
                    "name": item["name"],
                    "email": item["email"],
                    "registeredAt": item["registeredAt"],
                    "source": item.get("source", "unknown"),
                }
                for item in REGISTRATIONS
            ]
            self._send_json(200, public)
            return
        if path == "/api/last-submission":
            if not REGISTRATIONS:
                self._send_json(200, None)
                return
            latest = REGISTRATIONS[-1]
            self._send_json(
                200,
                {
                    "registrationId": latest["registrationId"],
                    "name": latest["name"],
                    "email": latest["email"],
                    "password": latest["password"],
                    "registeredAt": latest["registeredAt"],
                    "source": latest.get("source", "unknown"),
                },
            )
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/register":
            self._send_json(404, {"error": "Not found"})
            return

        try:
            payload = self._read_json_body()
        except (json.JSONDecodeError, ValueError) as error:
            self._send_json(400, {"error": str(error)})
            return

        name = str(payload.get("name") or "").strip()
        email = str(payload.get("email") or "").strip()
        password = str(payload.get("password") or "")

        missing = [
            key
            for key, value in (
                ("name", name),
                ("email", email),
                ("password", password),
            )
            if not value
        ]
        if missing:
            self._send_json(
                400,
                {"error": f"Missing required fields: {', '.join(missing)}"},
            )
            return

        registration_id = str(uuid.uuid4())
        entry = {
            "registrationId": registration_id,
            "name": name,
            "email": email,
            "password": password,
            "registeredAt": _now_iso(),
            "source": str(payload.get("source") or "api"),
        }
        REGISTRATIONS.append(entry)

        print(
            f"[demo-forms] Registered {name} <{email}> id={registration_id} "
            f"source={entry['source']}"
        )

        self._send_json(
            201,
            {
                "status": "registered",
                "registrationId": registration_id,
                "name": name,
                "email": email,
            },
        )


def main() -> None:
    server = HTTPServer((HOST, PORT), DemoFormsHandler)
    print(f"--- Demo Forms Server http://{HOST}:{PORT}/register ---")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n--- Demo Forms Server stopped ---")


if __name__ == "__main__":
    main()
