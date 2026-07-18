from __future__ import annotations

from abc import ABC, abstractmethod

from app.provider.dto import (
    ProviderCapabilities,
    YouTubeChannelData,
    YouTubePlaylistData,
    YouTubePlaylistPage,
    YouTubeVideoData,
)


class ProviderAdapter(ABC):
    """Abstract interface for provider-specific API adapters.

    Every adapter fetches raw data from a provider API and maps the
    response into immutable DTOs. No persistence, no progress tracking,
    no checkpoint logic — only fetch + transform.
    """

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Declared limits and feature support for this provider."""

    @abstractmethod
    async def get_channel(
        self,
        access_token: str,
    ) -> YouTubeChannelData | None:
        """Fetch the authenticated user's channel/profile.

        Returns the channel DTO, or None if no channel exists for the
        given token.
        """

    @abstractmethod
    async def get_upload_playlist(
        self,
        access_token: str,
        channel_id: str,
    ) -> YouTubePlaylistData | None:
        """Resolve the channel's upload playlist.

        Returns the playlist DTO, or None if no upload playlist exists.
        """

    @abstractmethod
    async def get_upload_playlist_page(
        self,
        access_token: str,
        playlist_id: str,
        page_token: str | None = None,
    ) -> YouTubePlaylistPage:
        """Fetch one page of video IDs from an upload playlist.

        Returns a page DTO with video IDs and the next page token
        (if more pages are available).
        """

    @abstractmethod
    async def get_video_batch(
        self,
        access_token: str,
        video_ids: list[str],
    ) -> list[YouTubeVideoData]:
        """Fetch metadata for a batch of video IDs (max 50).

        Returns a list of video DTOs, one per successfully fetched
        video. Invalid or missing IDs are silently skipped.
        """
