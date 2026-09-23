import asyncio
import json
from starlette.requests import Request
from transport.webhook_signature import verify_webhook_signature
from workflow.models import ContinuationNotification
from workflow.workflow_context import webhook_continuation


async def handle_bridge_webhook_request(
        request: Request,
) -> tuple[dict, int]:
    # Read raw body bytes to verify HMAC signature
    raw_body = await request.body()
    ok, error = verify_webhook_signature(
        raw_body,
        request.headers.get("X-Webhook-Signature"),
        request.headers.get("X-Webhook-Timestamp"),
        request.headers.get("X-Webhook-Nonce"),
    )
    if not ok:
        return {"detail": error}, 401

    try:
        payload = json.loads(raw_body)
        notification = ContinuationNotification(**payload)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"detail": "Invalid webhook JSON body"}, 400

    return await asyncio.to_thread(process_bridge_webhook, notification)


def process_bridge_webhook(
        notification: ContinuationNotification,
) -> tuple[dict, int]:
    handled = webhook_continuation.handle(notification)

    if not handled:
        return (
            {
                "detail": (
                    "No pending workflow found for request "
                    f"{notification.requestId}"
                ),
            },
            404,
        )

    return (
        {
            "status": "ok",
            "requestId": notification.requestId,
        },
        200,
    )