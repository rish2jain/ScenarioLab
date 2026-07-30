"""Optional shared-secret gate for /api/* (local lab stays open when unset)."""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

# Paths that remain reachable without the shared secret (health probes, root).
_PUBLIC_PREFIXES = (
    "/api/health",
    "/api/ready",
)

# OpenAPI/docs only exist when debug is on; still protect them if secret is set.
_PROTECTED_DOCS_PATHS = frozenset({"/docs", "/redoc", "/openapi.json"})


def _extract_shared_secret(request: Request) -> str | None:
    header = request.headers.get("x-scenariolab-secret")
    if header and header.strip():
        return header.strip()
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def _is_protected_docs_path(path: str) -> bool:
    if path in _PROTECTED_DOCS_PATHS:
        return True
    return path.startswith("/docs/") or path.startswith("/redoc/")


class SharedSecretAuthMiddleware(BaseHTTPMiddleware):
    """When ``settings.api_shared_secret`` is set, require it on /api/* and docs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        expected = (settings.api_shared_secret or "").strip()
        if not expected:
            return await call_next(request)

        path = request.url.path
        if path == "/" or any(path == p or path.startswith(p + "/") for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        # Non-/api paths are open except documentation endpoints (see comment above).
        if not path.startswith("/api") and not _is_protected_docs_path(path):
            return await call_next(request)

        provided = _extract_shared_secret(request)
        if provided is None or not secrets.compare_digest(
            provided.encode("utf-8"),
            expected.encode("utf-8"),
        ):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": (
                        "API shared secret required. " "Send X-ScenarioLab-Secret or Authorization: Bearer <secret>."
                    )
                },
            )
        return await call_next(request)
