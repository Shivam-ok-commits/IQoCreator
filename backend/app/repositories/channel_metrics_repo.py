from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChannelMetrics


class ChannelMetricsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_latest(self, creator_profile_id: UUID) -> ChannelMetrics | None:
        result = await self._db.execute(
            select(ChannelMetrics)
            .where(ChannelMetrics.creator_profile_id == creator_profile_id)
            .order_by(ChannelMetrics.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        creator_profile_id: UUID,
        subscriber_count: int | None,
        total_views: int | None,
        total_videos: int | None,
    ) -> tuple[ChannelMetrics, bool]:
        existing = await self.get_latest(creator_profile_id)
        now = datetime.now(timezone.utc)

        if existing:
            existing.recorded_at = now
            existing.subscriber_count = subscriber_count
            existing.total_views = total_views
            existing.total_videos = total_videos
            return existing, False

        metrics = ChannelMetrics(
            creator_profile_id=creator_profile_id,
            recorded_at=now,
            subscriber_count=subscriber_count,
            total_views=total_views,
            total_videos=total_videos,
        )
        self._db.add(metrics)
        return metrics, True
