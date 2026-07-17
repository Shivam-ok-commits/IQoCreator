from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CreatorProfile


class CreatorProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, profile_id: UUID) -> CreatorProfile | None:
        result = await self._db.execute(
            select(CreatorProfile).where(CreatorProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_platform(
        self, user_id: UUID, platform: str
    ) -> CreatorProfile | None:
        result = await self._db.execute(
            select(CreatorProfile).where(
                CreatorProfile.user_id == user_id,
                CreatorProfile.platform == platform,
            )
        )
        return result.scalar_one_or_none()

    async def update_from_channel(
        self, profile: CreatorProfile, channel: dict
    ) -> None:
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})
        branding = channel.get("brandingSettings", {})

        profile.name = snippet.get("title", profile.name)
        handle = snippet.get("customUrl")
        if handle:
            profile.handle = handle
        description = snippet.get("description")
        if description:
            profile.description = description
        country = snippet.get("country")
        if country:
            profile.country = country
        thumbnails = snippet.get("thumbnails", {})
        if thumbnails:
            thumb = thumbnails.get("default", thumbnails.get("high", {}))
            thumbnail_url = thumb.get("url")
            if thumbnail_url:
                profile.thumbnail_url = thumbnail_url
        banner = branding.get("image", {}).get("bannerExternalUrl")
        if banner:
            profile.banner_url = banner

        from app.utils import safe_int

        subscriber_count = safe_int(stats.get("subscriberCount"))
        if subscriber_count is not None:
            profile.subscriber_count = subscriber_count
        total_views = safe_int(stats.get("viewCount"))
        if total_views is not None:
            profile.total_views = total_views
