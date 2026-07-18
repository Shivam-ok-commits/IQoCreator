"""IQoCreator Backend — FastAPI Application.

This module initializes and configures the FastAPI application,
including middleware, CORS, exception handlers, and route registration.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.imports import router as import_router
from app.coordinator.exceptions import (
    ConnectedAccountNotFoundError,
    CoordinatorError,
    TokenAcquisitionError,
)
from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan context manager.

    Handles startup and shutdown events:
    - Startup: Initialize connections, caches, etc.
    - Shutdown: Gracefully close connections.
    """
    # Startup logic
    yield
    # Shutdown logic


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# ── Middleware ──────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ─────────────────────────────────────────────────


@app.exception_handler(ConnectedAccountNotFoundError)
async def connected_account_not_found_handler(
    _request: Request, exc: ConnectedAccountNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(TokenAcquisitionError)
async def token_acquisition_error_handler(
    _request: Request, exc: TokenAcquisitionError
) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(CoordinatorError)
async def coordinator_error_handler(
    _request: Request, exc: CoordinatorError
) -> JSONResponse:
    logger.exception("Unhandled coordinator error")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ── Routes ──────────────────────────────────────────────────────────────

app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(import_router)

# ── Root Endpoint ───────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint — returns basic API information."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }
