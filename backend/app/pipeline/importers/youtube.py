from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChannelMetrics, ConnectedAccount, CreatorProfile, ImportRun, ImportRunStatus
from app.pipeline.importers.base import BaseImporter, ImportResult

YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"


class YouTubeImporter(BaseImporter):
    """Import a YouTube channel's profile and current metrics."""

    async def run(
        self,
        creator_profile_id: UUID,
        access_token: str,
    ) -> ImportResult:
        """Fetch the channel from the YouTube API and persist the data."""

        # 1. Create an ImportRun (mark in-progress)
        run = ImportRun(
            creator_profile_id=creator_profile_id,
            status=ImportRunStatus.RUNNING,
            source="youtube_api",
            started_at=datetime.now(timezone.utc),
        )
        self._db.add(run)
        await self._db.flush()

        try:
            # 2. Fetch channel data from YouTube
            channel = await self._fetch_channel(access_token)
            if not channel:
                run.status = ImportRunStatus.FAILED
                run.error_message = "No channel found for this account"
                await self._db.flush()
                return ImportResult(
                    success=False,
                    creator_profile_id=creator_profile_id,
                    import_run_id=run.id,
                    message="No YouTube channel found",
                    error_message="No channel found for this account",
                )

            # 3. Upsert CreatorProfile
            profile = await self._upsert_profile(creator_profile_id, channel)
            profile_id = profile.id

            # 4. Snapshot channel metrics
            stats = channel.get("statistics", {})
            metrics = ChannelMetrics(
                creator_profile_id=profile_id,
                recorded_at=datetime.now(timezone.utc),
                subscriber_count=self._safe_int(stats.get("subscriberCount")),
                total_views=self._safe_int(stats.get("viewCount")),
                total_videos=self._safe_int(stats.get("videoCount")),
            )
            self._db.add(metrics)

            # 5. Mark import successful
            run.status = ImportRunStatus.COMPLETED
            run.completed_at = datetime.now(timezone.utc)
            await self._db.flush()

            return ImportResult(
                success=True,
                creator_profile_id=profile_id,
                import_run_id=run.id,
                message="Channel imported successfully",
            )

        except Exception as exc:
            run.status = ImportRunStatus.FAILED
            run.error_message = str(exc)
            await self._db.flush()
            return ImportResult(
                success=False,
                creator_profile_id=creator_profile_id,
                import_run_id=run.id,
                message="Channel import failed",
                error_message=str(exc),
            )

    async def _fetch_channel(self, access_token: str) -> dict | None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                YOUTUBE_CHANNELS_URL,
                params={"part": "snippet,statistics", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data.get("items", [])
            return items[0] if items else None

    async def _upsert_profile(
        self,
        creator_profile_id: UUID,
        channel: dict,
    ) -> CreatorProfile:
        result = await self._db.execute(
            select(CreatorProfile).where(CreatorProfile.id == creator_profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise ValueError(f"CreatorProfile {creator_profile_id} not found")

        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})

        profile.name = snippet.get("title", profile.name)
        handle = snippet.get("customUrl")
        if handle:
            profile.handle = handle
        description = snippet.get("description")
        if description:
            profile.description = description
        thumbnails = snippet.get("thumbnails", {})
        if thumbnails:
            for key in ("maxres", "standard", "high", "medium", "default"):
                entry = thumbnails.get(key)
                if entry and isinstance(entry, dict):
                    url = entry.get("url")
                    if url:
                        profile.thumbnail_url = url
                        break
        subscriber_count = self._safe_int(stats.get("subscriberCount"))
        if subscriber_count is not None:
            profile.subscriber_count = subscriber_count
        total_views = self._safe_int(stats.get("viewCount"))
        if total_views is not None:
            profile.total_views = total_views

        await self._db.flush()
        return profile

    @staticmethod
    def _safe_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def bind(self, db: AsyncSession) -> None:
        """Bind a database session to this importer instance."""
        self._db = db
