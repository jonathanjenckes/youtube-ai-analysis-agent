"""Health routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    """Return basic process health."""

    settings = request.app.state.settings
    return {"status": "ok", "environment": settings.app_env}
