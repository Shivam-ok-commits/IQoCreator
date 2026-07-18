"""YouTube video metadata retrieval.

Handles upload playlist discovery, paginated video ID collection,
and batch video metadata fetch. No database access, no lifecycle
management — pure API interaction + transformation to DTOs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx

from app.importers.youtube_types import PlaylistPageResult, YouTubeVideoData
from app.utils.duration import parse_iso8601_duration

logger = logging.getLogger(__name__)

YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"

DEFAULT_MAX_RESULTS = 50


class YouTubeVideoFetcher:
    """YouTube API interaction for video import.

    Three public operations:
      1. discover_upload_playlist_id()  — resolve the uploads playlist
      2. paginate_playlist()            — collect video IDs page by page
      3. fetch_video_batch()            — retrieve metadata for up to 50 IDs
    """

    async def discover_upload_playlist_id(
        self, access_token: str, channel_id: str
    ) -> str | None:
        """Resolve the channel's uploads playlist ID from the API.

        Returns None if the channel has no uploads playlist or is
        inaccessible.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                YOUTUBE_CHANNELS_URL,
                params={
                    "part": "contentDetails",
                    "id": channel_id,
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if resp.status_code != 200:
            logger.warning("Failed to fetch channel details: %s", resp.status_code)
            return None

        data: dict[str, Any] = resp.json()
        items = data.get("items", [])
        if not items:
            logger.warning("No channel found for id=%s", channel_id)
            return None

        content_details = items[0].get("contentDetails", {})
        related = content_details.get("relatedPlaylists", {})
        playlist_id = related.get("uploads")

        if playlist_id:
            logger.info("Discovered upload playlist: %s", playlist_id)
        else:
            logger.warning("Channel has no uploads playlist")

        return playlist_id

    async def paginate_playlist(
        self,
        access_token: str,
        playlist_id: str,
        page_token: str | None = None,
        page_number: int = 1,
    ) -> PlaylistPageResult:
        """Fetch one page of video IDs from a playlist.

        Returns the collected video IDs, the next page token (if any),
        and an optional total estimate from the API.
        """
        params: dict[str, Any] = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": DEFAULT_MAX_RESULTS,
        }
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                YOUTUBE_PLAYLIST_ITEMS_URL,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if resp.status_code != 200:
            logger.error(
                "Playlist page %d failed: %s", page_number, resp.status_code
            )
            return PlaylistPageResult(
                video_ids=(),
                next_page_token=None,
                page_number=page_number,
            )

        data: dict[str, Any] = resp.json()
        items: list[dict[str, Any]] = data.get("items", [])
        page_info = data.get("pageInfo", {})

        video_ids: list[str] = []
        for item in items:
            snippet = item.get("snippet", {})
            resource_id = snippet.get("resourceId", {})
            video_id = resource_id.get("videoId")
            if video_id:
                video_ids.append(video_id)

        next_token = data.get("nextPageToken")
        total_estimate = page_info.get("totalResults")

        logger.info(
            "Page %d fetched (%d IDs, next=%s, total=%s)",
            page_number,
            len(video_ids),
            next_token or "none",
            total_estimate or "unknown",
        )

        return PlaylistPageResult(
            video_ids=tuple(video_ids),
            next_page_token=next_token,
            page_number=page_number,
            total_estimate=total_estimate,
        )

    async def fetch_video_batch(
        self,
        access_token: str,
        video_ids: list[str],
        creator_profile_id: UUID,
    ) -> list[YouTubeVideoData]:
        """Fetch metadata for up to 50 video IDs.

        Transforms the YouTube API response into YouTubeVideoData DTOs.
        """
        if not video_ids:
            return []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                YOUTUBE_VIDEOS_URL,
                params={
                    "part": "snippet,contentDetails",
                    "id": ",".join(video_ids),
                    "maxResults": DEFAULT_MAX_RESULTS,
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if resp.status_code != 200:
            logger.error("Video batch fetch failed: %s", resp.status_code)
            return []

        data: dict[str, Any] = resp.json()
        items: list[dict[str, Any]] = data.get("items", [])

        videos: list[YouTubeVideoData] = []
        for item in items:
            video = self._transform_item(item, creator_profile_id)
            if video is not None:
                videos.append(video)

        logger.info("Batch complete: requested %d, received %d", len(video_ids), len(videos))
        return videos

    @staticmethod
    def _transform_item(
        item: dict[str, Any],
        creator_profile_id: UUID,
    ) -> YouTubeVideoData | None:
        """Transform a raw YouTube API video item into a YouTubeVideoData DTO."""
        video_id: str | None = item.get("id")
        if not video_id:
            return None

        snippet: dict[str, Any] = item.get("snippet", {})
        content_details: dict[str, Any] = item.get("contentDetails", {})

        title = snippet.get("title", "")
        if not title:
            return None

        description = snippet.get("description")
        thumbnails = snippet.get("thumbnails", {})
        thumb = thumbnails.get("default", thumbnails.get("high", {}))
        thumbnail_url = thumb.get("url") if thumb else None

        published_raw = snippet.get("publishedAt")
        published_at = None
        if published_raw:
            try:
                published_at = datetime.fromisoformat(
                    published_raw.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        duration_raw = content_details.get("duration")
        duration_seconds = parse_iso8601_duration(duration_raw)

        language = (
            snippet.get("defaultLanguage")
            or snippet.get("defaultAudioLanguage")
        )

        privacy_status = content_details.get("privacyStatus")
        category_id = snippet.get("categoryId")

        raw_tags: list[Any] | None = snippet.get("tags")
        tags: tuple[str, ...] = ()
        if raw_tags:
            tags = tuple(str(t) for t in raw_tags if isinstance(t, str))

        return YouTubeVideoData(
            creator_profile_id=creator_profile_id,
            platform_video_id=video_id,
            title=title,
            description=description or None,
            thumbnail_url=thumbnail_url or None,
            published_at=published_at,
            duration_seconds=duration_seconds,
            url=YOUTUBE_WATCH_URL.format(video_id=video_id),
            language=language or None,
            privacy_status=privacy_status or None,
            category_id=str(category_id) if category_id else None,
            tags=tags,
        )
