from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VideoImportRequest(BaseModel):
    creator_profile_id: UUID
    connected_account_id: UUID


class VideoImportResponse(BaseModel):
    status: str
    inserted: int = 0
    updated: int = 0
    processed: int = 0
    duration_ms: int = 0
    run_id: UUID


class ErrorResponse(BaseModel):
    detail: str


class ChannelImportResponse(BaseModel):
    success: bool
    imported: int = 0
    updated: int = 0
    duration_ms: int = 0
    error: str | None = None


class ImportRunResponse(BaseModel):
    id: str
    status: str
    videos_imported: int = 0
    videos_failed: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ImportStatusResponse(BaseModel):
    imported: bool
    last_imported_at: datetime | None = None
    runs: list[ImportRunResponse] = Field(default_factory=list)
