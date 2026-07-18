from __future__ import annotations

from typing import Any

import pytest

from app.provider.adapters.youtube_adapter import YouTubeAdapter


@pytest.fixture
def adapter() -> YouTubeAdapter:
    return YouTubeAdapter()


@pytest.fixture
def sample_channel_item() -> dict[str, Any]:
    return {
        "id": "UC_test_channel_123",
        "snippet": {
            "title": "Test Creator",
            "description": "A test YouTube channel",
            "customUrl": "@testcreator",
            "publishedAt": "2020-01-15T10:00:00Z",
            "country": "US",
            "thumbnails": {
                "default": {"url": "https://example.com/thumb.jpg"},
                "high": {"url": "https://example.com/thumb_hq.jpg"},
            },
        },
        "statistics": {
            "subscriberCount": "50000",
            "viewCount": "10000000",
            "videoCount": "200",
        },
        "brandingSettings": {
            "image": {
                "bannerExternalUrl": "https://example.com/banner.jpg",
            },
        },
    }


@pytest.fixture
def sample_channel_content_details() -> dict[str, Any]:
    return {
        "items": [
            {
                "contentDetails": {
                    "relatedPlaylists": {
                        "uploads": "UU_test_playlist_456",
                    },
                },
            },
        ],
    }


@pytest.fixture
def sample_playlist_page() -> dict[str, Any]:
    return {
        "items": [
            {
                "snippet": {
                    "resourceId": {"videoId": "video_001"},
                },
            },
            {
                "snippet": {
                    "resourceId": {"videoId": "video_002"},
                },
            },
        ],
        "nextPageToken": "CAUQAA",
        "pageInfo": {
            "totalResults": 200,
            "resultsPerPage": 50,
        },
    }


@pytest.fixture
def sample_video_response(sample_video_items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"items": sample_video_items}


@pytest.fixture
def sample_video_items() -> list[dict[str, Any]]:
    return [
        {
            "id": "video_001",
            "snippet": {
                "title": "Test Video 1",
                "description": "First test video",
                "publishedAt": "2023-06-01T14:00:00Z",
                "thumbnails": {
                    "default": {"url": "https://example.com/vid1.jpg"},
                },
                "tags": ["tag1", "tag2"],
                "categoryId": "22",
                "defaultLanguage": "en",
            },
            "contentDetails": {
                "duration": "PT10M30S",
                "privacyStatus": "public",
            },
        },
        {
            "id": "video_002",
            "snippet": {
                "title": "Test Video 2",
                "description": "Second test video",
                "publishedAt": "2023-07-15T09:30:00Z",
                "thumbnails": {
                    "default": {"url": "https://example.com/vid2.jpg"},
                },
                "tags": ["tag3"],
            },
            "contentDetails": {
                "duration": "PT5M",
                "privacyStatus": "public",
            },
        },
    ]
