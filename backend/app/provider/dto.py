from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ProviderCapabilities:
    """Declared capabilities of a provider adapter.

    Allows job-level code to make decisions based on what the
    provider supports, without hardcoding provider-specific limits.
    """

    supports_resume: bool = False
    supports_batch_fetch: bool = False
    max_batch_size: int = 1
    max_page_size: int = 50


@dataclass(frozen=True)
class YouTubeChannelData:
    channel_id: str
    title: str
    description: str | None = None
    custom_url: str | None = None
    thumbnail_url: str | None = None
    subscriber_count: int | None = None
    video_count: int | None = None
    view_count: int | None = None
    country: str | None = None
    banner_url: str | None = None
    upload_playlist_id: str | None = None
    joined_at: datetime | None = None


@dataclass(frozen=True)
class YouTubePlaylistData:
    playlist_id: str
    title: str | None = None
    item_count: int | None = None


@dataclass(frozen=True)
class YouTubePlaylistPage:
    video_ids: tuple[str, ...]
    next_page_token: str | None = None
    estimated_total: int | None = None


@dataclass(frozen=True)
class YouTubeVideoData:
    video_id: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    published_at: datetime | None = None
    duration_seconds: int | None = None
    url: str | None = None
    language: str | None = None
    privacy_status: str | None = None
    category_id: str | None = None
    tags: tuple[str, ...] = ()
