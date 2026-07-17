from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.importers.base import (
    BaseImporter,
    ChannelImportMetadata,
    ImportError,
    ImportResult,
)
from app.repositories import (
    ChannelMetricsRepository,
    CreatorProfileRepository,
    ImportRunRepository,
)
from app.utils import safe_int

YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"


class YouTubeImporter(BaseImporter):
    def __init__(self) -> None:
        self._profile_repo: CreatorProfileRepository | None = None
        self._metrics_repo: ChannelMetricsRepository | None = None
        self._run_repo: ImportRunRepository | None = None

    async def run(
        self,
        creator_profile_id: UUID,
        access_token: str,
    ) -> ImportResult:
        started_at = datetime.now(timezone.utc)
        imported = 0
        updated = 0

        run = await self._run_repo.create(creator_profile_id)

        fetch_result = await self._fetch_channel(access_token)
        if fetch_result is None:
            await self._run_repo.fail(run, "No YouTube channel found for this account")
            return ImportResult(
                success=False,
                failed=1,
                duration_ms=self._elapsed_ms(started_at),
                errors=[ImportError(item="channel", message="No YouTube channel found for this account")],
            )
        if isinstance(fetch_result, str):
            await self._run_repo.fail(run, fetch_result)
            return ImportResult(
                success=False,
                failed=1,
                duration_ms=self._elapsed_ms(started_at),
                errors=[ImportError(item="channel", message=fetch_result)],
            )
        channel = fetch_result

        profile = await self._profile_repo.get_by_id(creator_profile_id)
        if not profile:
            await self._run_repo.fail(run, f"CreatorProfile {creator_profile_id} not found")
            return ImportResult(
                success=False,
                failed=1,
                duration_ms=self._elapsed_ms(started_at),
                errors=[ImportError(item="profile", message=f"CreatorProfile {creator_profile_id} not found")],
            )

        await self._profile_repo.update_from_channel(profile, channel)
        updated += 1

        stats = channel.get("statistics", {})
        _, is_new = await self._metrics_repo.upsert(
            creator_profile_id=creator_profile_id,
            subscriber_count=safe_int(stats.get("subscriberCount")),
            total_views=safe_int(stats.get("viewCount")),
            total_videos=safe_int(stats.get("videoCount")),
        )
        if is_new:
            imported += 1
        else:
            updated += 1

        await self._run_repo.complete(run)

        return ImportResult(
            success=True,
            imported=imported,
            updated=updated,
            duration_ms=self._elapsed_ms(started_at),
            metadata=ChannelImportMetadata(
                channel_name=profile.name,
                handle=profile.handle,
                subscriber_count=profile.subscriber_count,
                video_count=safe_int(stats.get("videoCount")),
                view_count=safe_int(stats.get("viewCount")),
            ),
        )

    async def _fetch_channel(self, access_token: str) -> dict | str | None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                YOUTUBE_CHANNELS_URL,
                params={"part": "snippet,statistics,brandingSettings", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 401:
                return "Access token expired. Reconnect your YouTube account."
            if resp.status_code == 403:
                return "YouTube API access denied. Check your account permissions."
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data.get("items", [])
            return items[0] if items else None

    def bind(self, db: AsyncSession) -> None:
        self._profile_repo = CreatorProfileRepository(db)
        self._metrics_repo = ChannelMetricsRepository(db)
        self._run_repo = ImportRunRepository(db)

    @staticmethod
    def _elapsed_ms(since: datetime) -> int:
        return int((datetime.now(timezone.utc) - since).total_seconds() * 1000)
