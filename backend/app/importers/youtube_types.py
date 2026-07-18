"""YouTube-specific data types for the import pipeline.

These DTOs decouple internal code from raw YouTube API JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class YouTubeVideoData:
    """A single video's metadata as returned by the YouTube Data API.

    Immutable by design — created in the transformer and consumed
    by the VideoRepository. Never modified after construction.
    """

    creator_profile_id: UUID
    platform_video_id: str
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


@dataclass(frozen=True)
class PlaylistPageResult:
    """Result of a single playlist items page fetch."""

    video_ids: tuple[str, ...]
    next_page_token: str | None
    page_number: int
    total_estimate: int | None = None
