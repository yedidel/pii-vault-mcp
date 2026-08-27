from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from transport.adapter_auth import (
    is_local_vault_resolve,
    is_public_adapter_path,
    verify_adapter_auth,
)


class AdapterAuthMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        if is_public_adapter_path(request.url.path, request.method):
            await self.app(scope, receive, send)
            return

        if is_local_vault_resolve(request):
            await self.app(scope, receive, send)
            return

        ok, error = verify_adapter_auth(request)
        if not ok:
            response = JSONResponse({"detail": error}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)