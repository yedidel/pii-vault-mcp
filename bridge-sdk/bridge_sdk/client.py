"""High-level Bridge SDK client."""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any
from urllib.parse import urlparse, urlunparse

from bridge_sdk.events import register_session, wait_for_workflow_event
from bridge_sdk.exceptions import BridgeError, BridgeTimeoutError, PairingRequiredError
from bridge_sdk.mcp_client import DEFAULT_MCP_URL, McpTransport, SDK_PLATFORM
from bridge_sdk.models import (
    DEFAULT_DEMO_FORM_URL,
    ActionResult,
    ActionStatus,
    TERMINAL_STATUSES,
)


def _adapter_base_from_mcp_url(mcp_url: str) -> str:
    parsed = urlparse(mcp_url)
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def _events_url_from_mcp_url(mcp_url: str) -> str:
    override = os.getenv("BRIDGE_EVENTS_URL", "").strip()
    if override:
        return override.rstrip("/")
    parsed = urlparse(mcp_url)
    return urlunparse((parsed.scheme, parsed.netloc, "/events", "", "", ""))


def _new_session_id() -> str:
    return f"sdk-{uuid.uuid4().hex}"


class BridgeClient:
    """
    Python SDK for The Bridge — import and call methods.

    One method per action type:
      - send_payment / send_payment_and_wait
      - send_fill_form / send_fill_form_and_wait
      - send_transaction / send_transaction_and_wait
      - store_pii

    Or use run(...) to send + handle pairing + wait in one call.
    """

    def __init__(
            self,
            *,
            mcp_url: str | None = None,
            session_id: str | None = None,
            platform: str = SDK_PLATFORM,
    ) -> None:
        self.mcp_url = (mcp_url or DEFAULT_MCP_URL).rstrip("/")
        self.session_id = (session_id or _new_session_id()).strip()
        self.platform = platform.strip().lower() or SDK_PLATFORM
        self._transport: McpTransport | None = None
        self._sse_token: str | None = None

    async def __aenter__(self) -> "BridgeClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @property
    def adapter_base_url(self) -> str:
        return _adapter_base_from_mcp_url(self.mcp_url)

    @property
    def events_url(self) -> str:
        return _events_url_from_mcp_url(self.mcp_url)

    async def connect(self) -> None:
        self._transport = McpTransport(
            session_id=self.session_id,
            mcp_url=self.mcp_url,
            platform=self.platform,
        )
        await self._transport.connect()
        self._sse_token = await register_session(
            adapter_base_url=self.adapter_base_url,
            platform=self.platform,
            session_id=self.session_id,
        )

    async def close(self) -> None:
        if self._transport is not None:
            await self._transport.close()
            self._transport = None

    def _require_transport(self) -> McpTransport:
        if self._transport is None:
            raise RuntimeError("BridgeClient is not connected; use async with BridgeClient()")
        return self._transport

    @staticmethod
    def _raise_if_error(payload: dict[str, Any]) -> None:
        if payload.get("error") != "pairing_required":
            return
        raise PairingRequiredError(
            str(payload.get("message") or "Vault pairing required"),
            pairing_code=str(payload.get("pairingCode") or "").strip(),
            qr_url=str(payload.get("qrUrl") or "").strip(),
            expires_at=str(payload.get("expiresAt") or "").strip(),
        )

    async def send_action(
            self,
            *,
            agent_id: str,
            action_type: str,
            parameters: dict[str, str],
    ) -> ActionResult:
        transport = self._require_transport()
        payload = await transport.call_tool(
            "send_action",
            {
                "agentId": agent_id,
                "actionType": action_type,
                "parameters": parameters,
            },
        )
        if "error" in payload:
            self._raise_if_error(payload)
            raise BridgeError(str(payload.get("error")))
        return ActionResult.from_dict(payload)

    async def send_payment(
            self,
            *,
            amount: str,
            currency: str,
            agent_id: str = "agent-123",
    ) -> ActionResult:
        return await self.send_action(
            agent_id=agent_id,
            action_type="PAYMENT",
            parameters={"amount": str(amount), "currency": str(currency)},
        )

    async def send_fill_form(
            self,
            *,
            name: str,
            email: str,
            password: str,
            form_url: str | None = None,
            agent_id: str = "agent-123",
    ) -> ActionResult:
        parameters: dict[str, str] = {
            "name": str(name),
            "email": str(email),
            "password": str(password),
        }
        if form_url:
            parameters["formUrl"] = str(form_url)
        return await self.send_action(
            agent_id=agent_id,
            action_type="FILL_FORM",
            parameters=parameters,
        )

    async def send_transaction(
            self,
            *,
            transaction_id: str,
            account: str,
            agent_id: str = "agent-123",
    ) -> ActionResult:
        return await self.send_action(
            agent_id=agent_id,
            action_type="TRANSACTION",
            parameters={
                "transactionId": str(transaction_id),
                "account": str(account),
            },
        )

    async def store_pii(self, *, field_type: str, value: str) -> str:
        """
        Encrypt a value locally in the Adapter vault; returns vault:// token.
        Usually not needed — FILL_FORM encrypts email/password automatically.
        """
        transport = self._require_transport()
        payload = await transport.call_tool(
            "store_pii",
            {"fieldType": field_type, "value": value},
        )
        if "error" in payload:
            raise BridgeError(str(payload.get("error")))
        token = str(payload.get("token") or "").strip()
        if not token:
            raise BridgeError("store_pii returned no token")
        return token

    async def get_action_status(self, request_id: str) -> ActionStatus:
        transport = self._require_transport()
        payload = await transport.call_tool(
            "get_action_status",
            {"request_id": request_id},
        )
        if "error" in payload:
            raise BridgeError(str(payload.get("error")))
        return ActionStatus.from_dict(payload)

    async def wait_for_completion(
            self,
            request_id: str,
            *,
            timeout: float = 120.0,
            poll_interval: float = 2.0,
            use_sse: bool = False,
    ) -> ActionStatus:
        """
        Wait until the action reaches a terminal status.

        use_sse=False (default): poll get_action_status via MCP.
        use_sse=True: block on Adapter SSE (requires platform=sdk wake provider).
        """
        request_id = request_id.strip()
        if not request_id:
            raise ValueError("request_id is required")

        if use_sse:
            if not self._sse_token:
                raise RuntimeError("SSE token missing; call connect() first")
            event = await asyncio.wait_for(
                wait_for_workflow_event(
                    events_url=self.events_url,
                    platform=self.platform,
                    session_id=self.session_id,
                    token=self._sse_token,
                    request_id=request_id,
                ),
                timeout=timeout,
            )
            status = str(event.get("status") or "").strip()
            return ActionStatus(
                request_id=request_id,
                status=status,
                raw=event,
            )

        deadline = asyncio.get_running_loop().time() + timeout
        last: ActionStatus | None = None

        while asyncio.get_running_loop().time() < deadline:
            last = await self.get_action_status(request_id)
            if last.is_terminal:
                return last
            await asyncio.sleep(poll_interval)

        raise BridgeTimeoutError(
            f"Action {request_id!r} did not complete within {timeout}s "
            f"(last status={getattr(last, 'status', None)!r})"
        )

    async def send_payment_and_wait(
            self,
            *,
            amount: str,
            currency: str,
            agent_id: str = "agent-123",
            timeout: float = 120.0,
            use_sse: bool = False,
    ) -> ActionStatus:
        """send_payment + wait_for_completion in one call."""
        return await self.run(
            lambda: self.send_payment(
                amount=amount,
                currency=currency,
                agent_id=agent_id,
            ),
            timeout=timeout,
            use_sse=use_sse,
        )

    async def send_fill_form_and_wait(
            self,
            *,
            name: str,
            email: str,
            password: str,
            form_url: str | None = None,
            agent_id: str = "agent-123",
            timeout: float = 120.0,
            use_sse: bool = False,
    ) -> ActionStatus:
        return await self.run(
            lambda: self.send_fill_form(
                name=name,
                email=email,
                password=password,
                form_url=form_url,
                agent_id=agent_id,
            ),
            timeout=timeout,
            use_sse=use_sse,
        )

    async def send_transaction_and_wait(
            self,
            *,
            transaction_id: str,
            account: str,
            agent_id: str = "agent-123",
            timeout: float = 120.0,
            use_sse: bool = False,
    ) -> ActionStatus:
        return await self.run(
            lambda: self.send_transaction(
                transaction_id=transaction_id,
                account=account,
                agent_id=agent_id,
            ),
            timeout=timeout,
            use_sse=use_sse,
        )

    async def run(
            self,
            send_fn,
            *,
            timeout: float = 120.0,
            poll_interval: float = 2.0,
            pairing_timeout: float = 600.0,
            use_sse: bool = False,
            on_pairing_url: Any = None,
    ) -> ActionStatus:
        """
        Full flow: send → pairing if needed → wait for Vault → return status.

        send_fn: async callable that returns ActionResult, e.g.
            lambda: client.send_payment(amount="100", currency="ILS")
        on_pairing_url: optional callback(qr_url) when pairing is required.
        """
        try:
            result = await send_fn()
        except PairingRequiredError as error:
            if on_pairing_url is None:
                print(f"Pairing required: {error.qr_url}")
            result = await self.wait_for_pairing_and_retry(
                send_fn,
                poll_interval=poll_interval,
                timeout=pairing_timeout,
                on_pairing_url=on_pairing_url,
            )

        return await self.wait_for_completion(
            result.request_id,
            timeout=timeout,
            poll_interval=poll_interval,
            use_sse=use_sse,
        )

    async def wait_for_pairing_and_retry(
            self,
            action_callable,
            *,
            poll_interval: float = 2.0,
            timeout: float = 600.0,
            on_pairing_url: Any = None,
    ) -> ActionResult:
        """
        After PairingRequiredError, poll until send_action succeeds.

        action_callable: async callable returning ActionResult, e.g.
            lambda: client.send_payment(amount="100", currency="ILS")
        on_pairing_url: optional callback(qr_url: str) to print/open QR link.
        """
        deadline = asyncio.get_running_loop().time() + timeout
        last_error: Exception | None = None
        qr_shown = False

        while asyncio.get_running_loop().time() < deadline:
            try:
                return await action_callable()
            except PairingRequiredError as error:
                last_error = error
                if on_pairing_url is not None and not qr_shown:
                    qr_shown = True
                    result = on_pairing_url(error.qr_url)
                    if asyncio.iscoroutine(result):
                        await result
                await asyncio.sleep(poll_interval)

        raise BridgeTimeoutError(
            f"Pairing not completed within {timeout}s"
        ) from last_error
