from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

import main
from continuation.polling_continuation import PollingContinuation
from logutil import get_logger
from workflow.models import ContinuationNotification

if TYPE_CHECKING:
    from workflow.workflow_service import WorkflowService

logger = get_logger(__name__)

_FINAL_STATUSES = frozenset({
    "COMPLETED",
    "REJECTED",
    "FAILED",
    "FAILED_APP_NOT_INSTALLED",
    "UNTRUSTED",
})

_DEFAULT_INTERVAL_SECONDS = 2.0
_DEFAULT_TIMEOUT_SECONDS = 120.0


def _poll_interval_seconds() -> float:
    raw = os.getenv("ADAPTER_POLL_INTERVAL_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_INTERVAL_SECONDS
    try:
        return max(0.5, float(raw))
    except ValueError:
        return _DEFAULT_INTERVAL_SECONDS


def _poll_timeout_seconds() -> float:
    raw = os.getenv("ADAPTER_POLL_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        return max(5.0, float(raw))
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS


def _is_final_status(status: str) -> bool:
    return (status or "").strip().upper() in _FINAL_STATUSES


class PollingWorker:
    """
    Poll Bridge GetActionStatus for pending POLLING workflows.

    Mirrors the webhook path: both call ContinuationService.handle() on completion.
    """

    def __init__(
            self,
            *,
            workflow_service: WorkflowService,
            polling_continuation: PollingContinuation,
    ) -> None:
        self._workflow_service = workflow_service
        self._polling_continuation = polling_continuation
        self._stop_event = asyncio.Event()
        self._interval_seconds = _poll_interval_seconds()
        self._timeout_seconds = _poll_timeout_seconds()

    def stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        logger.info(
            "Polling worker started interval=%ss timeout=%ss",
            self._interval_seconds,
            self._timeout_seconds,
        )
        while not self._stop_event.is_set():
            await self._poll_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._interval_seconds,
                )
            except asyncio.TimeoutError:
                continue

        logger.info("Polling worker stopped")

    async def _poll_once(self) -> None:
        pending = self._workflow_service.list_pending_polling()
        if not pending:
            return

        for workflow in pending:
            if self._stop_event.is_set():
                return

            if self._workflow_service.is_pending_timed_out(
                    workflow.requestId,
                    self._timeout_seconds,
            ):
                logger.warning(
                    "Polling timeout requestId=%s workflowId=%s",
                    workflow.requestId,
                    workflow.workflowId,
                )
                self._workflow_service.remove_workflow(workflow.requestId)
                continue

            try:
                status_response = await asyncio.to_thread(
                    main.get_status,
                    workflow.requestId,
                )
            except Exception as error:
                logger.warning(
                    "Polling get_status failed requestId=%s: %s",
                    workflow.requestId,
                    error,
                )
                continue

            current_status = str(status_response.get("status") or "").strip()
            if not _is_final_status(current_status):
                continue

            notification = ContinuationNotification(
                workflowId=workflow.workflowId,
                requestId=workflow.requestId,
                status=current_status,
                message=str(status_response.get("resultData") or "").strip()
                or f"Workflow reached {current_status}",
            )

            logger.info(
                "Polling detected final status requestId=%s status=%s",
                workflow.requestId,
                current_status,
            )

            # Continuation (including Gemini wake) must not block the
            # Adapter event loop or SSE cannot be delivered.
            handled = await asyncio.to_thread(
                self._polling_continuation.handle,
                notification,
            )
            if not handled:
                logger.warning(
                    "Polling handle skipped requestId=%s "
                    "(workflow no longer pending)",
                    workflow.requestId,
                )
