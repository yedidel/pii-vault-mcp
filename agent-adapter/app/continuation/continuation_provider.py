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
        return ContinuationTarget(
            connector_type=os.getenv("CONNECTOR_TYPE", "POLLING"),
            connector_context=os.getenv("CONNECTOR_CONTEXT", "")
        )