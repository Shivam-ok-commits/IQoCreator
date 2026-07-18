from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.provider.adapters.youtube_adapter import YouTubeAdapter
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
from app.provider.enum import Provider
from app.provider.adapters.base import ProviderAdapter
from app.provider.adapters.factory import ProviderAdapterFactory


# ── Factory ─────────────────────────────────────────────────────────────


class TestProviderAdapterFactory:
    def test_create_youtube_adapter(self) -> None:
        adapter = ProviderAdapterFactory.create(Provider.YOUTUBE)
        assert isinstance(adapter, YouTubeAdapter)

    def test_create_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="No adapter registered"):
            ProviderAdapterFactory.create("unknown")  # type: ignore[arg-type]

    def test_register_custom_adapter(self) -> None:
        class FakeAdapter(YouTubeAdapter):
            pass

        ProviderAdapterFactory.register(Provider.YOUTUBE, FakeAdapter)
        adapter = ProviderAdapterFactory.create(Provider.YOUTUBE)
        assert isinstance(adapter, FakeAdapter)

        # Restore
        ProviderAdapterFactory.register(Provider.YOUTUBE, YouTubeAdapter)


# ── get_channel ─────────────────────────────────────────────────────────


class TestGetChannel:
    async def test_returns_channel_data(
        self,
        adapter: YouTubeAdapter,
        sample_channel_item: dict[str, Any],
    ) -> None:
        resp_data: dict[str, Any] = {"items": [sample_channel_item]}
        with patch.object(adapter, "_request", AsyncMock(return_value=resp_data)):
            result = await adapter.get_channel("fake_token")

        assert result is not None
        assert isinstance(result, YouTubeChannelData)
        assert result.channel_id == "UC_test_channel_123"
        assert result.title == "Test Creator"
        assert result.description == "A test YouTube channel"
        assert result.custom_url == "@testcreator"
        assert result.subscriber_count == 50000
        assert result.view_count == 10_000_000
        assert result.video_count == 200
        assert result.country == "US"
        assert result.thumbnail_url == "https://example.com/thumb.jpg"
        assert result.banner_url == "https://example.com/banner.jpg"
        assert result.joined_at is not None

    async def test_returns_none_when_no_items(
        self,
        adapter: YouTubeAdapter,
    ) -> None:
        resp_data: dict[str, Any] = {"items": []}
        with patch.object(adapter, "_request", AsyncMock(return_value=resp_data)):
            result = await adapter.get_channel("fake_token")

        assert result is None

    async def test_raises_authentication_error_on_401(
        self,
        adapter: YouTubeAdapter,
    ) -> None:
        with patch.object(
            adapter,
            "_request",
            AsyncMock(side_effect=ProviderAuthenticationError("Token expired")),
        ), pytest.raises(ProviderAuthenticationError):
            await adapter.get_channel("bad_token")

    async def test_raises_rate_limit_error_on_429(
        self,
        adapter: YouTubeAdapter,
    ) -> None:
        with patch.object(
            adapter,
            "_request",
            AsyncMock(side_effect=ProviderRateLimitError("Rate limited")),
        ), pytest.raises(ProviderRateLimitError):
            await adapter.get_channel("fake_token")

    async def test_raises_api_error_on_403(
        self,
        adapter: YouTubeAdapter,
    ) -> None:
        with patch.object(
            adapter,
            "_request",
            AsyncMock(side_effect=ProviderApiError("Access denied")),
        ), pytest.raises(ProviderApiError):
            await adapter.get_channel("fake_token")


# ── get_upload_playlist ─────────────────────────────────────────────────


class TestGetUploadPlaylist:
    async def test_returns_playlist_data(
        self,
        adapter: YouTubeAdapter,
        sample_channel_content_details: dict[str, Any],
    ) -> None:
        with patch.object(
            adapter, "_request", AsyncMock(return_value=sample_channel_content_details)
        ):
            result = await adapter.get_upload_playlist(
                "fake_token", "UC_test_channel_123"
            )

        assert result is not None
        assert isinstance(result, YouTubePlaylistData)
        assert result.playlist_id == "UU_test_playlist_456"

    async def test_returns_none_when_no_uploads_playlist(
        self,
        adapter: YouTubeAdapter,
    ) -> None:
        resp_data: dict[str, Any] = {
            "items": [
                {
                    "contentDetails": {
                        "relatedPlaylists": {},
                    },
                },
            ],
        }
        with patch.object(adapter, "_request", AsyncMock(return_value=resp_data)):
            result = await adapter.get_upload_playlist(
                "fake_token", "UC_test_channel_123"
            )

        assert result is None

    async def test_returns_none_when_no_items(
        self,
        adapter: YouTubeAdapter,
    ) -> None:
        with patch.object(adapter, "_request", AsyncMock(return_value={"items": []})):
            result = await adapter.get_upload_playlist(
                "fake_token", "UC_test_channel_123"
            )

        assert result is None


# ── get_upload_playlist_page ────────────────────────────────────────────


class TestGetUploadPlaylistPage:
    async def test_returns_page_with_video_ids_and_token(
        self,
        adapter: YouTubeAdapter,
        sample_playlist_page: dict[str, Any],
    ) -> None:
        with patch.object(adapter, "_request", AsyncMock(return_value=sample_playlist_page)):
            result = await adapter.get_upload_playlist_page(
                "fake_token", "UU_test_playlist_456"
            )

        assert isinstance(result, YouTubePlaylistPage)
        assert result.video_ids == ("video_001", "video_002")
        assert result.next_page_token == "CAUQAA"
        assert result.estimated_total == 200

    async def test_passes_page_token(
        self,
        adapter: YouTubeAdapter,
        sample_playlist_page: dict[str, Any],
    ) -> None:
        mock_request = AsyncMock(return_value=sample_playlist_page)
        with patch.object(adapter, "_request", mock_request):
            await adapter.get_upload_playlist_page(
                "fake_token", "UU_test_playlist_456", page_token="CAUQAA"
            )

        # Verify pageToken was passed in the request params
        call_args = mock_request.call_args[1]
        params = call_args.get("params", {})
        assert params.get("pageToken") == "CAUQAA"

    async def test_returns_empty_page_when_no_items(
        self,
        adapter: YouTubeAdapter,
    ) -> None:
        resp_data: dict[str, Any] = {
            "items": [],
            "pageInfo": {"totalResults": 0, "resultsPerPage": 50},
        }
        with patch.object(adapter, "_request", AsyncMock(return_value=resp_data)):
            result = await adapter.get_upload_playlist_page(
                "fake_token", "UU_test_playlist_456"
            )

        assert result.video_ids == ()
        assert result.next_page_token is None
        assert result.estimated_total == 0


# ── get_video_batch ─────────────────────────────────────────────────────


class TestGetVideoBatch:
    async def test_returns_video_data_list(
        self,
        adapter: YouTubeAdapter,
        sample_video_response: dict[str, Any],
    ) -> None:
        with patch.object(adapter, "_request", AsyncMock(return_value=sample_video_response)):
            results = await adapter.get_video_batch(
                "fake_token", ["video_001", "video_002"]
            )

        assert len(results) == 2
        assert all(isinstance(v, YouTubeVideoData) for v in results)

        v1 = results[0]
        assert v1.video_id == "video_001"
        assert v1.title == "Test Video 1"
        assert v1.description == "First test video"
        assert v1.duration_seconds == 630  # 10m30s
        assert v1.language == "en"
        assert v1.privacy_status == "public"
        assert v1.category_id == "22"
        assert v1.tags == ("tag1", "tag2")
        assert v1.url == "https://www.youtube.com/watch?v=video_001"

        v2 = results[1]
        assert v2.video_id == "video_002"
        assert v2.title == "Test Video 2"
        assert v2.duration_seconds == 300  # 5m
        assert v2.language is None  # no defaultLanguage
        assert v2.tags == ("tag3",)

    async def test_returns_empty_list_for_no_ids(
        self,
        adapter: YouTubeAdapter,
    ) -> None:
        results = await adapter.get_video_batch("fake_token", [])
        assert results == []

    async def test_skips_items_without_id(
        self,
        adapter: YouTubeAdapter,
    ) -> None:
        resp_data: dict[str, Any] = {
            "items": [
                {"snippet": {"title": "No ID"}},
                {"id": "valid_id", "snippet": {"title": "Valid Video"}},
            ],
        }
        with patch.object(adapter, "_request", AsyncMock(return_value=resp_data)):
            results = await adapter.get_video_batch("fake_token", ["valid_id"])

        assert len(results) == 1
        assert results[0].video_id == "valid_id"

    async def test_skips_items_without_title(
        self,
        adapter: YouTubeAdapter,
    ) -> None:
        resp_data: dict[str, Any] = {
            "items": [
                {"id": "no_title", "snippet": {}},
                {
                    "id": "good_id",
                    "snippet": {"title": "Good Video"},
                    "contentDetails": {},
                },
            ],
        }
        with patch.object(adapter, "_request", AsyncMock(return_value=resp_data)):
            results = await adapter.get_video_batch(
                "fake_token", ["no_title", "good_id"]
            )

        assert len(results) == 1
        assert results[0].video_id == "good_id"


# ── DTO immutability ────────────────────────────────────────────────────


class TestDTOImmutability:
    def test_channel_data_is_frozen(self) -> None:
        dto = YouTubeChannelData(channel_id="id", title="Title")
        with pytest.raises(AttributeError):
            dto.title = "New Title"  # type: ignore[misc]

    def test_playlist_data_is_frozen(self) -> None:
        dto = YouTubePlaylistData(playlist_id="id")
        with pytest.raises(AttributeError):
            dto.playlist_id = "new_id"  # type: ignore[misc]

    def test_playlist_page_is_frozen(self) -> None:
        dto = YouTubePlaylistPage(video_ids=("a", "b"))
        with pytest.raises(AttributeError):
            dto.video_ids = ()  # type: ignore[misc]

    def test_video_data_is_frozen(self) -> None:
        dto = YouTubeVideoData(video_id="id", title="Title")
        with pytest.raises(AttributeError):
            dto.title = "New Title"  # type: ignore[misc]

    def test_channel_data_defaults(self) -> None:
        dto = YouTubeChannelData(channel_id="id", title="Title")
        assert dto.description is None
        assert dto.subscriber_count is None
        assert dto.upload_playlist_id is None

    def test_video_data_defaults(self) -> None:
        dto = YouTubeVideoData(video_id="id", title="Title")
        assert dto.tags == ()
        assert dto.language is None
        assert dto.duration_seconds is None


# ── Typed exceptions ────────────────────────────────────────────────────


class TestTypedExceptions:
    def test_exception_hierarchy(self) -> None:
        assert issubclass(ProviderAuthenticationError, Exception)
        assert issubclass(ProviderRateLimitError, Exception)
        assert issubclass(ProviderApiError, Exception)
        assert issubclass(ProviderUnavailableError, Exception)

    def test_exception_messages(self) -> None:
        err = ProviderAuthenticationError("Token expired")
        assert str(err) == "Token expired"


# ── ProviderCapabilities ────────────────────────────────────────────────


class TestProviderCapabilities:
    def test_capabilities_is_frozen(self) -> None:
        caps = ProviderCapabilities()
        with pytest.raises(AttributeError):
            caps.supports_resume = False  # type: ignore[misc]

    def test_youtube_adapter_exposes_capabilities(self) -> None:
        adapter = YouTubeAdapter()
        caps = adapter.capabilities
        assert isinstance(caps, ProviderCapabilities)

    def test_youtube_capabilities_values(self) -> None:
        adapter = YouTubeAdapter()
        caps = adapter.capabilities
        assert caps.supports_resume is True
        assert caps.supports_batch_fetch is True
        assert caps.max_batch_size == 50
        assert caps.max_page_size == 50

    def test_default_values(self) -> None:
        caps = ProviderCapabilities()
        assert caps.supports_resume is False
        assert caps.supports_batch_fetch is False
        assert caps.max_batch_size == 1
        assert caps.max_page_size == 50

    def test_capabilities_accessible_via_abstract_interface(self) -> None:
        adapter: ProviderAdapter = YouTubeAdapter()
        caps = adapter.capabilities
        assert caps.supports_batch_fetch is True


# ── HTTP error mapping (_request) ───────────────────────────────────────


class TestRequestErrorMapping:
    """Test that _request correctly maps HTTP status codes to typed exceptions."""

    @staticmethod
    def _make_response(status: int, json_data: dict[str, Any] | None = None) -> Mock:
        resp = Mock()
        resp.status_code = status
        resp.json.return_value = json_data or {}
        resp.text = "Error"
        return resp

    async def test_401_raises_authentication_error(self) -> None:
        adapter = YouTubeAdapter()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=self._make_response(401))
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            with pytest.raises(ProviderAuthenticationError):
                await adapter.get_channel("bad_token")

    async def test_403_raises_api_error(self) -> None:
        adapter = YouTubeAdapter()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=self._make_response(403))
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            with pytest.raises(ProviderApiError):
                await adapter.get_channel("bad_token")

    async def test_429_raises_rate_limit_error(self) -> None:
        adapter = YouTubeAdapter()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=self._make_response(429))
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            with pytest.raises(ProviderRateLimitError):
                await adapter.get_channel("fake_token")

    async def test_500_raises_api_error(self) -> None:
        adapter = YouTubeAdapter()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_resp = self._make_response(500)
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            with pytest.raises(ProviderApiError):
                await adapter.get_channel("fake_token")

    async def test_200_returns_json(self) -> None:
        adapter = YouTubeAdapter()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=self._make_response(200, {"items": []})
            )
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            result = await adapter.get_channel("fake_token")
            assert result is None  # no items

    async def test_raises_unavailable_on_timeout(self) -> None:
        adapter = YouTubeAdapter()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = __import__("httpx").TimeoutException(
                "Connection timed out"
            )
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value = mock_client

            with pytest.raises(ProviderUnavailableError):
                await adapter.get_channel("fake_token")
