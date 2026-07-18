from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ImportContext:
    import_run_id: UUID
    creator_profile_id: UUID
    connected_account_id: UUID
    provider: str
    started_at: datetime


@dataclass
class ImportState:
    processed: int = 0
    total: int = 0
    next_page_token: str | None = None
    retries: int = 0
