from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ImportRun, ImportRunStatus


class ImportRunRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        creator_profile_id: UUID,
        source: str = "youtube",
    ) -> ImportRun:
        run = ImportRun(
            creator_profile_id=creator_profile_id,
            status=ImportRunStatus.RUNNING,
            source=source,
            started_at=datetime.now(timezone.utc),
        )
        self._db.add(run)
        return run

    async def complete(self, run: ImportRun) -> None:
        run.status = ImportRunStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)

    async def fail(self, run: ImportRun, error_message: str) -> None:
        run.status = ImportRunStatus.FAILED
        run.error_message = error_message
        run.completed_at = datetime.now(timezone.utc)

    async def get_recent_by_profile(
        self, creator_profile_id: UUID, limit: int = 5
    ) -> list[ImportRun]:
        result = await self._db.execute(
            select(ImportRun)
            .where(ImportRun.creator_profile_id == creator_profile_id)
            .order_by(ImportRun.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
