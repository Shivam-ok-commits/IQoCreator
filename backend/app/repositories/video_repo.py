from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Video


class VideoRepository:
    """Database access for Video records.

    Handles idempotent upsert and lookup. No pagination or API logic.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upsert(self, video: Video) -> tuple[Video, bool]:
        """Insert or update a single video by platform_video_id.

        Returns (video, is_new).
        """
        existing = await self.get_by_platform_id(
            video.creator_profile_id, video.platform_video_id
        )
        if existing:
            existing.title = video.title
            existing.description = video.description
            existing.thumbnail_url = video.thumbnail_url
            existing.published_at = video.published_at
            existing.duration_seconds = video.duration_seconds
            existing.url = video.url
            existing.language = video.language
            existing.privacy_status = video.privacy_status
            existing.category_id = video.category_id
            existing.tags = video.tags
            return existing, False

        self._db.add(video)
        return video, True

    async def bulk_upsert(
        self, videos: list[Video]
    ) -> tuple[list[Video], int, int]:
        """Bulk upsert videos using PostgreSQL INSERT … ON CONFLICT.

        Returns (all_videos, inserted_count, updated_count).
        """
        if not videos:
            return [], 0, 0

        stmt = pg_insert(Video).values(
            [
                {
                    "creator_profile_id": v.creator_profile_id,
                    "platform_video_id": v.platform_video_id,
                    "title": v.title,
                    "description": v.description,
                    "thumbnail_url": v.thumbnail_url,
                    "published_at": v.published_at,
                    "duration_seconds": v.duration_seconds,
                    "url": v.url,
                    "language": v.language,
                    "privacy_status": v.privacy_status,
                    "category_id": v.category_id,
                    "tags": v.tags,
                }
                for v in videos
            ]
        )

        do_update = stmt.on_conflict_do_update(
            index_elements=["platform_video_id"],
            set_={
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "thumbnail_url": stmt.excluded.thumbnail_url,
                "published_at": stmt.excluded.published_at,
                "duration_seconds": stmt.excluded.duration_seconds,
                "url": stmt.excluded.url,
                "language": stmt.excluded.language,
                "privacy_status": stmt.excluded.privacy_status,
                "category_id": stmt.excluded.category_id,
                "tags": stmt.excluded.tags,
            },
        )

        result = await self._db.execute(do_update)
        updated = result.rowcount if result.rowcount is not None else 0
        inserted = max(0, len(videos) - updated)

        return videos, inserted, updated

    async def get_by_platform_id(
        self, creator_profile_id: UUID, platform_video_id: str
    ) -> Video | None:
        result = await self._db.execute(
            select(Video).where(
                Video.creator_profile_id == creator_profile_id,
                Video.platform_video_id == platform_video_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_creator_profile(
        self, creator_profile_id: UUID
    ) -> list[Video]:
        result = await self._db.execute(
            select(Video).where(
                Video.creator_profile_id == creator_profile_id
            )
        )
        return list(result.scalars().all())
