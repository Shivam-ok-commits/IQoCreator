from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest
from unittest.mock import AsyncMock

from app.importers.base import ImportContext, ImportState
from app.jobs.base import ImportResult
from app.jobs.video_import_job import VideoImportJob
from app.provider.adapters.base import ProviderAdapter
from app.provider.dto import (
    ProviderCapabilities,
    YouTubeChannelData,
    YouTubePlaylistData,
    YouTubePlaylistPage,
    YouTubeVideoData,
)


CREATOR_PROFILE_ID = UUID("11111111-1111-1111-1111-111111111111")
CONNECTED_ACCOUNT_ID = UUID("22222222-2222-2222-2222-222222222222")
RUN_ID = UUID("33333333-3333-3333-3333-333333333333")
ACCESS_TOKEN = "test_access_token_123"
CHANNEL_ID = "UC_test_channel_xyz"
PLAYLIST_ID = "UU_test_playlist_xyz"


# ── Mock adapter ───────────────────────────────────────────────────────


@dataclass
class AdapterCall:
    method: str
    args: tuple[Any, ...] = ()


class MockYouTubeAdapter(ProviderAdapter):
    """A configurable mock that returns controlled DTOs."""

    def __init__(self) -> None:
        self._channel: YouTubeChannelData | None = YouTubeChannelData(
            channel_id=CHANNEL_ID,
            title="Test Creator",
        )
        self._playlist: YouTubePlaylistData | None = YouTubePlaylistData(
            playlist_id=PLAYLIST_ID,
        )
        self._pages: list[YouTubePlaylistPage] = []
        self._videos: dict[str, YouTubeVideoData] = {}
        self._fail_get_channel: Exception | None = None
        self._fail_get_upload_playlist: Exception | None = None
        self._fail_get_playlist_page: Exception | None = None
        self._fail_get_video_batch: Exception | None = None
        self._page_call_count: int = 0
        self._fail_after_page_calls: int | None = None
        self._fail_page_exc: Exception | None = None
        self._caps: ProviderCapabilities = ProviderCapabilities(
            supports_resume=True,
            supports_batch_fetch=True,
            max_batch_size=50,
            max_page_size=50,
        )
        self.calls: list[AdapterCall] = []

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._caps

    def set_capabilities(self, **kwargs: Any) -> None:
        self._caps = ProviderCapabilities(**kwargs)

    def set_channel(self, channel: YouTubeChannelData | None) -> None:
        self._channel = channel

    def set_playlist(self, playlist: YouTubePlaylistData | None) -> None:
        self._playlist = playlist

    def set_pages(self, pages: list[YouTubePlaylistPage]) -> None:
        self._pages = pages

    def add_videos(self, videos: list[YouTubeVideoData]) -> None:
        for v in videos:
            self._videos[v.video_id] = v

    def fail_get_channel(self, exc: Exception | None) -> None:
        self._fail_get_channel = exc

    def fail_get_upload_playlist(self, exc: Exception | None) -> None:
        self._fail_get_upload_playlist = exc

    def fail_get_playlist_page(self, exc: Exception | None) -> None:
        self._fail_get_playlist_page = exc

    def fail_after_n_page_calls(self, n: int, exc: Exception | None) -> None:
        self._fail_after_page_calls = n
        self._fail_page_exc = exc
        self._page_call_count = 0

    def fail_get_video_batch(self, exc: Exception | None) -> None:
        self._fail_get_video_batch = exc

    async def get_channel(self, access_token: str) -> YouTubeChannelData | None:
        self.calls.append(AdapterCall("get_channel", (access_token,)))
        if self._fail_get_channel:
            raise self._fail_get_channel
        return self._channel

    async def get_upload_playlist(
        self, access_token: str, channel_id: str
    ) -> YouTubePlaylistData | None:
        self.calls.append(
            AdapterCall("get_upload_playlist", (access_token, channel_id))
        )
        if self._fail_get_upload_playlist:
            raise self._fail_get_upload_playlist
        return self._playlist

    async def get_upload_playlist_page(
        self, access_token: str, playlist_id: str, page_token: str | None = None
    ) -> YouTubePlaylistPage:
        self.calls.append(
            AdapterCall(
                "get_upload_playlist_page", (access_token, playlist_id, page_token)
            )
        )
        if self._fail_get_playlist_page:
            raise self._fail_get_playlist_page
        self._page_call_count += 1
        if (
            self._fail_after_page_calls is not None
            and self._page_call_count >= self._fail_after_page_calls
            and self._fail_page_exc is not None
        ):
            raise self._fail_page_exc
        if not self._pages:
            return YouTubePlaylistPage(video_ids=())
        if page_token is None:
            return self._pages[0]
        for i, p in enumerate(self._pages):
            if p.next_page_token == page_token and i + 1 < len(self._pages):
                return self._pages[i + 1]
        return YouTubePlaylistPage(video_ids=())

    async def get_video_batch(
        self, access_token: str, video_ids: list[str]
    ) -> list[YouTubeVideoData]:
        self.calls.append(AdapterCall("get_video_batch", (access_token, video_ids)))
        if self._fail_get_video_batch:
            raise self._fail_get_video_batch
        return [self._videos[vid] for vid in video_ids if vid in self._videos]


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def context() -> ImportContext:
    return ImportContext(
        import_run_id=RUN_ID,
        creator_profile_id=CREATOR_PROFILE_ID,
        connected_account_id=CONNECTED_ACCOUNT_ID,
        provider="youtube",
        started_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def state() -> ImportState:
    return ImportState()


@pytest.fixture
def mock_video_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.bulk_upsert.return_value = ([], 0, 0)
    return repo


@pytest.fixture
def mock_run_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_adapter() -> MockYouTubeAdapter:
    return MockYouTubeAdapter()


def make_video_dto(
    video_id: str,
    title: str = "Test Video",
    **kwargs: Any,
) -> YouTubeVideoData:
    return YouTubeVideoData(
        video_id=video_id,
        title=title,
        **kwargs,
    )


def make_playlist_page(
    video_ids: list[str],
    next_page_token: str | None = None,
    estimated_total: int | None = None,
) -> YouTubePlaylistPage:
    return YouTubePlaylistPage(
        video_ids=tuple(video_ids),
        next_page_token=next_page_token,
        estimated_total=estimated_total,
    )


async def run_job(
    adapter: ProviderAdapter,
    video_repo: AsyncMock,
    run_repo: AsyncMock,
    context: ImportContext,
    state: ImportState | None = None,
) -> ImportResult:
    if state is None:
        state = ImportState()
    job = VideoImportJob(
        adapter=adapter,
        repository=video_repo,
        run_repo=run_repo,
        access_token=ACCESS_TOKEN,
    )
    return await job.execute(context, state)
