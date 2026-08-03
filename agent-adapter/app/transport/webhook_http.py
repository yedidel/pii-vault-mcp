from workflow.models import ContinuationNotification
from workflow.workflow_context import webhook_continuation


def process_bridge_webhook(
        notification: ContinuationNotification,
) -> tuple[dict, int]:
    # shared webhook handling for FastAPI (stdio mode)
    # and FastMCP custom_route (http mode)
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
