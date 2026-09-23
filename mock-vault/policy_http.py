"""
Local HTTP UI/API for Vault-owned privacy preferences.

Runs beside the Mock Vault WebSocket client. The policy file remains
the source of truth; this process never caches field decisions.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from policy_eval import (
    DEFAULT_POLICY_PATH,
    PolicyEvaluationError,
    demo_privacy_fields,
    load_policy,
    update_demo_privacy_fields,
)
from vault_field_values import (
    DEFAULT_VALUES_PATH,
    ensure_vault_only_values,
    load_values,
    update_field_values,
    values_for_ui,
)

HOST = os.getenv("VAULT_PRIVACY_HOST", "127.0.0.1")
PORT = int(os.getenv("VAULT_PRIVACY_PORT", "8020"))
PRIVACY_HTML_PATH = Path(__file__).resolve().parent / "privacy.html"


class PolicyHttpHandler(BaseHTTPRequestHandler):
    policy_path: Path = DEFAULT_POLICY_PATH
    values_path: Path = DEFAULT_VALUES_PATH

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        print(f"[mock-vault-http] {self.address_string()} - {format % args}")

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, "application/json; charset=utf-8", body)

    def _send_html(self, status: int, html: str) -> None:
        self._send(status, "text/html; charset=utf-8", html.encode("utf-8"))

    def _error(self, status: int, error: PolicyEvaluationError) -> None:
        http_status = status
        if error.code == "INVALID_USER_INSTALL":
            http_status = 403
        elif error.code == "INVALID_REQUEST":
            http_status = 400
        elif error.code == "MALFORMED_POLICY":
            http_status = 500
        self._send_json(
            http_status,
            {"error": error.message, "code": error.code},
        )

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

        if path in {"/privacy", "/"}:
            html = PRIVACY_HTML_PATH.read_text(encoding="utf-8")
            return self._send_html(200, html)

        if path == "/health":
            return self._send_json(200, {"status": "ok"})

        if path == "/api/privacy":
            query = parse_qs(parsed.query)
            provided = str((query.get("userInstallId") or [""])[0]).strip()
            try:
                policy = load_policy(self.policy_path)
                expected = str(policy.get("userInstallId") or "").strip()
                if provided and provided != expected:
                    raise PolicyEvaluationError(
                        "INVALID_USER_INSTALL",
                        "user_install_id does not match Vault policy identity",
                    )
                fields = demo_privacy_fields(policy)
                stored = values_for_ui(self.values_path)
            except PolicyEvaluationError as error:
                return self._error(400, error)
            return self._send_json(
                200,
                {
                    "userInstallId": str(policy.get("userInstallId") or ""),
                    "fields": fields,
                    "storedValues": stored,
                },
            )

        self._send_json(404, {"error": "Not found"})

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path != "/api/privacy":
            return self._send_json(404, {"error": "Not found"})

        payload = self._read_json_body()
        if payload is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        user_install_id = str(
            payload.get("userInstallId") or payload.get("user_install_id") or "",
        ).strip()
        fields = payload.get("fields")
        if not isinstance(fields, dict):
            return self._send_json(400, {"error": "fields must be an object"})
        incoming_values = payload.get("values")
        if incoming_values is None:
            incoming_values = {}
        if not isinstance(incoming_values, dict):
            return self._send_json(400, {"error": "values must be an object"})
        incoming_values = {
            str(key): "" if value is None else str(value)
            for key, value in incoming_values.items()
        }

        try:
            policy = load_policy(self.policy_path)
            expected = str(policy.get("userInstallId") or "").strip()
            if not expected or expected != user_install_id:
                raise PolicyEvaluationError(
                    "INVALID_USER_INSTALL",
                    "user_install_id does not match Vault policy identity",
                )
            stored_identity = str(
                load_values(self.values_path).get("userInstallId") or "",
            ).strip()
            if stored_identity and stored_identity != user_install_id:
                raise PolicyEvaluationError(
                    "INVALID_USER_INSTALL",
                    "user_install_id does not match Vault value identity",
                )
            current = demo_privacy_fields(policy)
            planned = dict(current)
            planned.update({
                str(key).strip().lower(): str(value).strip().upper()
                for key, value in fields.items()
            })
            ensure_vault_only_values(
                path=self.values_path,
                user_install_id=user_install_id,
                field_decisions=planned,
                incoming_values=incoming_values,
            )
            if incoming_values:
                update_field_values(
                    path=self.values_path,
                    user_install_id=user_install_id,
                    values=incoming_values,
                )
            updated = update_demo_privacy_fields(
                policy_path=self.policy_path,
                user_install_id=user_install_id,
                fields=fields,
            )
            policy = load_policy(self.policy_path)
            stored = values_for_ui(self.values_path)
        except PolicyEvaluationError as error:
            return self._error(400, error)

        return self._send_json(
            200,
            {
                "userInstallId": str(policy.get("userInstallId") or ""),
                "fields": updated,
                "storedValues": stored,
                "saved": True,
            },
        )


def start_policy_http_server(
        *,
        host: str = HOST,
        port: int = PORT,
        policy_path: Path = DEFAULT_POLICY_PATH,
        values_path: Path = DEFAULT_VALUES_PATH,
) -> ThreadingHTTPServer:
    handler = type(
        "BoundPolicyHttpHandler",
        (PolicyHttpHandler,),
        {"policy_path": policy_path, "values_path": values_path},
    )
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(
        target=server.serve_forever,
        name="mock-vault-privacy-http",
        daemon=True,
    )
    thread.start()
    return server
