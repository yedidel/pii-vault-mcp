import hashlib
import hmac as hm
import os
import time
import unittest

from transport import webhook_signature as ws
from transport.webhook_signature import verify_webhook_signature


class WebhookHmacTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["WEBHOOK_SECRET"] = "test-secret"
        self.body = b'{"requestId":"r1","workflowId":"w1","status":"COMPLETED","message":"ok"}'

    def _sign(self, timestamp: str, nonce: str) -> str:
        payload = f"{timestamp}.{nonce}.".encode("utf-8") + self.body
        return ws.PREFIX + hm.new(b"test-secret", payload, hashlib.sha256).hexdigest()

    def test_valid_hmac_accepted(self) -> None:
        timestamp = str(int(time.time()))
        nonce = "n-valid"
        ok, err = verify_webhook_signature(
            self.body,
            self._sign(timestamp, nonce),
            timestamp,
            nonce,
        )
        self.assertTrue(ok, err)

    def test_invalid_hmac_rejected(self) -> None:
        ok, err = verify_webhook_signature(
            self.body,
            f"{ws.PREFIX}deadbeef",
            str(int(time.time())),
            "nonce-invalid",
        )
        self.assertFalse(ok)
        self.assertIsNotNone(err)

    def test_nonce_replay_rejected(self) -> None:
        timestamp = str(int(time.time()))
        nonce = "replay-nonce"
        header = self._sign(timestamp, nonce)
        ok1, _ = verify_webhook_signature(self.body, header, timestamp, nonce)
        ok2, err2 = verify_webhook_signature(self.body, header, timestamp, nonce)
        self.assertTrue(ok1)
        self.assertFalse(ok2)
        self.assertIn("replay", (err2 or "").lower())


if __name__ == "__main__":
    unittest.main()
