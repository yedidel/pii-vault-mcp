from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from vault_store import PiiVaultStore


def is_localhost_client(request: Request) -> bool:
    client = request.client
    if client is None:
        return False
    return client.host in {"127.0.0.1", "::1", "localhost"}


def resolve_vault_refs(store: PiiVaultStore, refs: list) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for ref in refs:
        ref_text = str(ref).strip()
        if not ref_text:
            continue
        resolved[ref_text] = store.resolve(ref_text)
    return resolved


async def handle_vault_resolve_request(
        request: Request,
        store: PiiVaultStore,
) -> Response:
    if not is_localhost_client(request):
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    refs = payload.get("refs")
    if not isinstance(refs, list) or not refs:
        return JSONResponse(
            {"error": "refs must be a non-empty array"},
            status_code=400,
        )

    try:
        resolved = resolve_vault_refs(store, refs)
    except (KeyError, ValueError) as error:
        return JSONResponse({"error": str(error)}, status_code=404)

    return JSONResponse({"resolved": resolved})
