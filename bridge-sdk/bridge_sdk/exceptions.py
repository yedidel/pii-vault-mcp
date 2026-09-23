"""SDK exceptions."""

from __future__ import annotations


class BridgeError(Exception):
    """Base error for bridge-sdk."""


class BridgeTimeoutError(BridgeError):
    """Action did not reach a terminal status in time."""


class PairingRequiredError(BridgeError):
    """Vault is not paired; user must open qrUrl and connect Mock Vault."""

    def __init__(
            self,
            message: str,
            *,
            pairing_code: str = "",
            qr_url: str = "",
            expires_at: str = "",
    ) -> None:
        super().__init__(message)
        self.pairing_code = pairing_code
        self.qr_url = qr_url
        self.expires_at = expires_at
