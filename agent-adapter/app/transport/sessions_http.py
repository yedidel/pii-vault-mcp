from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from session_registry import SessionConflictError, SessionRegistry


async def handle_session_register(
        request: Request,
        registry: SessionRegistry,
        user_install_id: str,
) -> Response:
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON body"}, status_code=400)

    if not isinstance(payload, dict):
        return JSONResponse({"detail": "JSON body must be an object"}, status_code=400)

    platform = str(payload.get("platform") or "").strip().lower()
    session_id = str(payload.get("sessionId") or "").strip()
    ingress_url = str(payload.get("ingressUrl") or "").strip() or None

    if not platform or not session_id:
        return JSONResponse(
            {
                "detail": (
                    "Fields 'platform' and 'sessionId' are required"
                ),
            },
            status_code=400,
        )

    try:
        record = registry.register(
            user_install_id,
            platform,
            session_id,
            ingress_url=ingress_url,
        )
    except SessionConflictError as error:
        return JSONResponse({"detail": str(error)}, status_code=403)
    except ValueError as error:
        return JSONResponse({"detail": str(error)}, status_code=400)

    return JSONResponse(
        {
            "platform": record.platform,
            "sessionId": record.session_id,
            "sseToken": record.sse_token,
            "expiresAt": record.expires_at.isoformat(),
        }
    )
