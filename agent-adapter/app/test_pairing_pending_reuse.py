import threading
import tempfile
import unittest
from pathlib import Path

from install_directory_client import InstallLookup, PairStartResult
from pairing_service import PairingRequired, PairingResolved, PairingService
from pairing_store import PairingStore


class FakeDirectory:
    def __init__(self, base_url: str = "http://127.0.0.1:8010") -> None:
        self.base_url = base_url
        self._next_index = 0
        self.starts = 0
        self.pairings: dict[str, dict] = {}
        self.installs: dict[str, InstallLookup] = {}

    def start_pairing(self) -> PairStartResult:
        self.starts += 1
        self._next_index += 1
        code = f"code-{self._next_index}"
        self.pairings[code] = {
            "pairingCode": code,
            "status": "PENDING",
            "expiresAt": "2099-01-01T00:00:00+00:00",
            "expired": False,
        }
        return PairStartResult(
            pairing_code=code,
            qr_url=f"{self.base_url}/pair?code={code}",
            expires_at="2099-01-01T00:00:00+00:00",
        )

    def get_pairing(self, pairing_code: str) -> dict:
        if pairing_code not in self.pairings:
            raise RuntimeError("pairing_code not found")
        return dict(self.pairings[pairing_code])

    def get_install(self, user_install_id: str) -> InstallLookup | None:
        return self.installs.get(user_install_id)

    def complete(self, pairing_code: str, user_install_id: str) -> None:
        self.pairings[pairing_code] = {
            "pairingCode": pairing_code,
            "status": "COMPLETED",
            "expiresAt": "2099-01-01T00:00:00+00:00",
            "expired": False,
            "userInstallId": user_install_id,
        }
        self.installs[user_install_id] = InstallLookup(
            user_install_id=user_install_id,
            vault_service_url="ws://127.0.0.1:8081/vault-websocket",
            status="ACTIVE",
        )

    def expire(self, pairing_code: str) -> None:
        body = dict(self.pairings[pairing_code])
        body["expired"] = True
        self.pairings[pairing_code] = body


class PairingPendingReuseTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = PairingStore(Path(self._tmp.name) / "pairing.json")
        self.directory = FakeDirectory()
        self.service = PairingService(
            store=self.store,
            directory=self.directory,
            legacy_user_install_id="legacy-install",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _resolve(self) -> PairingRequired | PairingResolved:
        return self.service.resolve(
            platform="sdk",
            session_id="sdk-same-session",
            action_summary="PAYMENT agentId=agent-123",
        )

    def test_first_resolve_starts_one_pairing(self) -> None:
        outcome = self._resolve()
        self.assertIsInstance(outcome, PairingRequired)
        self.assertEqual(outcome.pairing_code, "code-1")
        self.assertEqual(self.directory.starts, 1)
        state = self.store.load()
        self.assertEqual(state.pending_pairing_code, "code-1")

    def test_second_resolve_while_pending_reuses_code(self) -> None:
        first = self._resolve()
        second = self._resolve()
        self.assertIsInstance(first, PairingRequired)
        self.assertIsInstance(second, PairingRequired)
        self.assertEqual(first.pairing_code, second.pairing_code)
        self.assertEqual(self.directory.starts, 1)

    def test_repeated_retries_do_not_create_new_codes(self) -> None:
        codes = []
        for _ in range(8):
            outcome = self._resolve()
            self.assertIsInstance(outcome, PairingRequired)
            codes.append(outcome.pairing_code)
        self.assertEqual(set(codes), {"code-1"})
        self.assertEqual(self.directory.starts, 1)

    def test_completed_pairing_stores_user_install_id(self) -> None:
        first = self._resolve()
        assert isinstance(first, PairingRequired)
        self.directory.complete(first.pairing_code, "install_abc")
        outcome = self._resolve()
        self.assertIsInstance(outcome, PairingResolved)
        self.assertEqual(outcome.user_install_id, "install_abc")

    def test_pending_fields_cleared_after_complete(self) -> None:
        first = self._resolve()
        assert isinstance(first, PairingRequired)
        self.directory.complete(first.pairing_code, "install_abc")
        self.service.check_pending_pairing()
        state = self.store.load()
        self.assertEqual(state.user_install_id, "install_abc")
        self.assertIsNone(state.pending_pairing_code)
        self.assertIsNone(state.pending_platform)
        self.assertIsNone(state.pending_session_id)
        self.assertIsNone(state.pending_action_summary)
        self.assertIsNotNone(state.paired_at)

    def test_next_resolve_does_not_request_pairing(self) -> None:
        first = self._resolve()
        assert isinstance(first, PairingRequired)
        self.directory.complete(first.pairing_code, "install_abc")
        self._resolve()
        again = self._resolve()
        self.assertIsInstance(again, PairingResolved)
        self.assertEqual(self.directory.starts, 1)

    def test_expired_pairing_creates_new_code(self) -> None:
        first = self._resolve()
        assert isinstance(first, PairingRequired)
        self.directory.expire(first.pairing_code)
        second = self._resolve()
        self.assertIsInstance(second, PairingRequired)
        self.assertEqual(second.pairing_code, "code-2")
        self.assertEqual(self.directory.starts, 2)

    def test_set_pending_does_not_overwrite_paired_install(self) -> None:
        self.store.set_paired("install_keep")
        self.store.set_pending_pairing(
            "code-stale",
            platform="sdk",
            session_id="sdk-x",
        )
        state = self.store.load()
        self.assertEqual(state.user_install_id, "install_keep")
        self.assertIsNone(state.pending_pairing_code)

    def test_concurrent_complete_and_resolve_keep_install(self) -> None:
        first = self._resolve()
        assert isinstance(first, PairingRequired)
        self.directory.complete(first.pairing_code, "install_race")
        errors: list[str] = []

        def complete() -> None:
            self.service.check_pending_pairing()

        def retry() -> None:
            outcome = self._resolve()
            if isinstance(outcome, PairingRequired):
                errors.append(outcome.pairing_code)

        threads = [
            threading.Thread(target=complete),
            threading.Thread(target=retry),
            threading.Thread(target=retry),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        state = self.store.load()
        self.assertEqual(state.user_install_id, "install_race")
        self.assertIsNone(state.pending_pairing_code)
        self.assertEqual(self.directory.starts, 1)


if __name__ == "__main__":
    unittest.main()
