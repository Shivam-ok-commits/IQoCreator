from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from app.provider.adapters.base import ProviderAdapter
from app.provider.dto import (
    ProviderCapabilities,
    YouTubeChannelData,
    YouTubePlaylistData,
    YouTubePlaylistPage,
    YouTubeVideoData,
)
from app.provider.exceptions import (
    ProviderApiError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.utils.duration import parse_iso8601_duration

logger = logging.getLogger(__name__)

_THUMBNAIL_PRIORITY = ("maxres", "standard", "high", "medium", "default")


def _best_thumbnail(thumbnails: dict[str, Any]) -> str | None:
    """Return the URL of the highest-resolution thumbnail available.

    Priority: maxres → standard → high → medium → default.
    Returns None when no thumbnails exist.
    """
    for key in _THUMBNAIL_PRIORITY:
        entry = thumbnails.get(key)
        if entry and isinstance(entry, dict):
            url = entry.get("url")
            if url and isinstance(url, str):
                return url
    return None

YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"

DEFAULT_MAX_RESULTS = 50


class YouTubeAdapter(ProviderAdapter):
    """YouTube Data API v3 adapter.

    Handles all YouTube-specific HTTP requests, response parsing, and
    DTO mapping. No persistence, no repositories, no import-run state.
    """

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_resume=True,
            supports_batch_fetch=True,
            max_batch_size=50,
            max_page_size=50,
        )

    async def get_channel(
        self,
        access_token: str,
    ) -> YouTubeChannelData | None:
        data = await self._request(
            url=YOUTUBE_CHANNELS_URL,
            params={
                "part": "snippet,statistics,brandingSettings",
                "mine": "true",
            },
            access_token=access_token,
        )
        items = data.get("items", [])
        if not items:
            return None
        return self._map_channel(items[0])

    async def get_upload_playlist(
        self,
        access_token: str,
        channel_id: str,
    ) -> YouTubePlaylistData | None:
        data = await self._request(
            url=YOUTUBE_CHANNELS_URL,
            params={
                "part": "contentDetails",
                "id": channel_id,
            },
            access_token=access_token,
        )
        items = data.get("items", [])
        if not items:
            return None
        content_details = items[0].get("contentDetails", {})
        related = content_details.get("relatedPlaylists", {})
        playlist_id = related.get("uploads")
        if not playlist_id:
            return None
        return YouTubePlaylistData(
            playlist_id=playlist_id,
        )

    async def get_upload_playlist_page(
        self,
        access_token: str,
        playlist_id: str,
        page_token: str | None = None,
    ) -> YouTubePlaylistPage:
        params: dict[str, Any] = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": DEFAULT_MAX_RESULTS,
        }
        if page_token:
            params["pageToken"] = page_token

        data = await self._request(
            url=YOUTUBE_PLAYLIST_ITEMS_URL,
            params=params,
            access_token=access_token,
        )
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

        return YouTubePlaylistPage(
            video_ids=tuple(video_ids),
            next_page_token=next_token,
            estimated_total=total_estimate,
        )

    async def get_video_batch(
        self,
        access_token: str,
        video_ids: list[str],
    ) -> list[YouTubeVideoData]:
        if not video_ids:
            return []

        data = await self._request(
            url=YOUTUBE_VIDEOS_URL,
            params={
                "part": "snippet,contentDetails",
                "id": ",".join(video_ids),
                "maxResults": DEFAULT_MAX_RESULTS,
            },
            access_token=access_token,
        )
        items: list[dict[str, Any]] = data.get("items", [])

        videos: list[YouTubeVideoData] = []
        for item in items:
            video = self._map_video(item)
            if video is not None:
                videos.append(video)

        return videos

    # ── Internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _map_channel(item: dict[str, Any]) -> YouTubeChannelData:
        snippet: dict[str, Any] = item.get("snippet", {})
        stats: dict[str, Any] = item.get("statistics", {})
        branding: dict[str, Any] = item.get("brandingSettings", {})

        channel_id: str = item.get("id", "")
        title: str = snippet.get("title", "")
        description: str | None = snippet.get("description")
        custom_url: str | None = snippet.get("customUrl")
        country: str | None = snippet.get("country")

        thumbnail_url = _best_thumbnail(snippet.get("thumbnails", {}))

        banner = branding.get("image", {}).get("bannerExternalUrl")
        banner_url: str | None = str(banner) if banner else None

        joined_raw = snippet.get("publishedAt")
        joined_at: datetime | None = None
        if joined_raw:
            try:
                joined_at = datetime.fromisoformat(
                    joined_raw.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        return YouTubeChannelData(
            channel_id=channel_id,
            title=title,
            description=description,
            custom_url=custom_url,
            thumbnail_url=thumbnail_url,
            subscriber_count=_safe_int(stats.get("subscriberCount")),
            video_count=_safe_int(stats.get("videoCount")),
            view_count=_safe_int(stats.get("viewCount")),
            country=country,
            banner_url=banner_url,
            joined_at=joined_at,
        )

    @staticmethod
    def _map_video(item: dict[str, Any]) -> YouTubeVideoData | None:
        video_id: str | None = item.get("id")
        if not video_id:
            return None

        snippet: dict[str, Any] = item.get("snippet", {})
        content_details: dict[str, Any] = item.get("contentDetails", {})

        title = snippet.get("title", "")
        if not title:
            return None

        description = snippet.get("description", "")
        thumbnail_url = _best_thumbnail(snippet.get("thumbnails", {}))

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
            video_id=video_id,
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

    @staticmethod
    async def _request(
        url: str,
        params: dict[str, Any],
        access_token: str,
    ) -> dict[str, Any]:
        """Execute an authenticated GET request against the YouTube API.

        Raises typed exceptions for every non-2xx or connection error.
        Never returns raw error details to the caller — only the
        response JSON on success.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.TimeoutException:
            raise ProviderUnavailableError(
                f"YouTube API timed out: {url}"
            )
        except httpx.NetworkError as exc:
            raise ProviderUnavailableError(
                f"Network error connecting to YouTube API: {exc}"
            )

        if resp.status_code == 401:
            raise ProviderAuthenticationError(
                "Access token rejected by YouTube API. Reconnect your account."
            )
        if resp.status_code == 403:
            raise ProviderApiError(
                "YouTube API access denied. Check account permissions."
            )
        if resp.status_code == 429:
            raise ProviderRateLimitError(
                "YouTube API rate limit exceeded. Try again later."
            )
        if resp.status_code != 200:
            raise ProviderApiError(
                f"YouTube API returned HTTP {resp.status_code}: {resp.text[:200]}"
            )

        return resp.json()


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)  # type: ignore[call-overload]
    except (ValueError, TypeError):
        return None
