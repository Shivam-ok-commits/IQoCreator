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

    async def create_pending(
        self,
        creator_profile_id: UUID,
        source: str = "youtube",
    ) -> ImportRun:
        run = ImportRun(
            creator_profile_id=creator_profile_id,
            status=ImportRunStatus.PENDING,
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

    async def transition(
        self, run_id: UUID, status: ImportRunStatus
    ) -> ImportRun | None:
        result = await self._db.execute(
            select(ImportRun).where(ImportRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = status
        return run

    async def get_by_id(self, run_id: UUID) -> ImportRun | None:
        result = await self._db.execute(
            select(ImportRun).where(ImportRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def get_last_pending_or_running(
        self, creator_profile_id: UUID
    ) -> ImportRun | None:
        result = await self._db.execute(
            select(ImportRun)
            .where(
                ImportRun.creator_profile_id == creator_profile_id,
                ImportRun.status.in_(
                    [ImportRunStatus.PENDING, ImportRunStatus.RUNNING]
                ),
            )
            .order_by(ImportRun.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_checkpoint(
        self,
        run_id: UUID,
        next_page_token: str | None = None,
        processed_count: int | None = None,
        total_count: int | None = None,
        checkpoint_data: dict | None = None,
    ) -> None:
        result = await self._db.execute(
            select(ImportRun).where(ImportRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run:
            if next_page_token is not None:
                run.last_page_token = next_page_token
            if processed_count is not None:
                run.processed_count = processed_count
            if total_count is not None:
                run.total_count = total_count
            if checkpoint_data is not None:
                run.checkpoint_data = checkpoint_data

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
