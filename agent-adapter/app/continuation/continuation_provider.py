from dataclasses import dataclass
import os


@dataclass
class ContinuationTarget:
    connector_type: str
    connector_context: str


class ContinuationProvider:

    def resolve(self) -> ContinuationTarget:
        raise NotImplementedError


class DefaultContinuationProvider(ContinuationProvider):

    def resolve(self):
        # OpenAI / Claude async wake requires WEBHOOK back to the Adapter.
        # POLLING remains available by setting CONNECTOR_TYPE=POLLING.
        return ContinuationTarget(
            connector_type=os.getenv("CONNECTOR_TYPE", "WEBHOOK"),
            connector_context=os.getenv(
                "CONNECTOR_CONTEXT",
                "http://127.0.0.1:8000/webhook/bridge",
            ),
        )