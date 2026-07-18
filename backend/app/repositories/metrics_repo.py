"""MetricsRepository — persistence for MetricSnapshot artifacts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MetricSnapshot


class MetricsRepository:
    """Database access for MetricSnapshot records.

    Handles idempotent upsert and historical lookup. No analysis logic.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, snapshot: MetricSnapshot) -> MetricSnapshot:
        """Persist a new MetricSnapshot.

        Uses PostgreSQL INSERT … ON CONFLICT to guarantee idempotency
        on (creator_profile_id, snapshot_at).
        """
        stmt = pg_insert(MetricSnapshot).values(
            {
                "id": snapshot.id,
                "creator_profile_id": snapshot.creator_profile_id,
                "snapshot_at": snapshot.snapshot_at,
                "source_import_run_id": snapshot.source_import_run_id,
                "total_videos": snapshot.total_videos,
                "total_views": snapshot.total_views,
                "total_subscribers": snapshot.total_subscribers,
                "avg_views_per_video": snapshot.avg_views_per_video,
                "avg_view_duration_seconds": snapshot.avg_view_duration_seconds,
                "total_watch_time_hours": snapshot.total_watch_time_hours,
                "engagement_rate": snapshot.engagement_rate,
                "version": snapshot.version,
            }
        )

        do_update = stmt.on_conflict_do_update(
            index_elements=["creator_profile_id", "snapshot_at"],
            set_={
                "total_videos": stmt.excluded.total_videos,
                "total_views": stmt.excluded.total_views,
                "total_subscribers": stmt.excluded.total_subscribers,
                "avg_views_per_video": stmt.excluded.avg_views_per_video,
                "avg_view_duration_seconds": stmt.excluded.avg_view_duration_seconds,
                "total_watch_time_hours": stmt.excluded.total_watch_time_hours,
                "engagement_rate": stmt.excluded.engagement_rate,
                "version": stmt.excluded.version,
            },
        )

        await self._db.execute(do_update)
        return snapshot

    async def get_latest(self, creator_profile_id: UUID) -> MetricSnapshot | None:
        """Return the most recent MetricSnapshot for a creator."""
        result = await self._db.execute(
            select(MetricSnapshot)
            .where(MetricSnapshot.creator_profile_id == creator_profile_id)
            .order_by(MetricSnapshot.snapshot_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, snapshot_id: UUID) -> MetricSnapshot | None:
        """Return a MetricSnapshot by its ID."""
        result = await self._db.execute(
            select(MetricSnapshot).where(MetricSnapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()

    async def get_by_creator(
        self, creator_profile_id: UUID
    ) -> list[MetricSnapshot]:
        """Return all MetricSnapshots for a creator, newest first."""
        result = await self._db.execute(
            select(MetricSnapshot)
            .where(MetricSnapshot.creator_profile_id == creator_profile_id)
            .order_by(MetricSnapshot.snapshot_at.desc())
        )
        return list(result.scalars().all())

    async def count_by_creator(self, creator_profile_id: UUID) -> int:
        """Return the number of MetricSnapshots for a creator."""
        result = await self._db.execute(
            select(MetricSnapshot.id)
            .where(MetricSnapshot.creator_profile_id == creator_profile_id)
        )
        return len(result.scalars().all())
