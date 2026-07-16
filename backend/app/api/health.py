"""Health check endpoint.

Provides a simple health check for monitoring and orchestration tools.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return the health status of the API.

    Returns a simple JSON response indicating the service is running.
    Used by Docker health checks, load balancers, and monitoring tools.
    """
    return {"status": "ok"}
