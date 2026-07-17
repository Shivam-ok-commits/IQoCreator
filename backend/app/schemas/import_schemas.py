from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


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
