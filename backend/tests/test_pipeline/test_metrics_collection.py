"""Tests for MetricsCollectionStage and MetricsRepository.

Covers: successful collection, empty dataset, replay/idempotency,
historical snapshots, incremental updates, repository persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models import CreatorProfile, MetricSnapshot
from app.pipeline.metrics_collection_stage import (
    MetricsCollectionStage,
    MetricsContext,
)
from app.repositories.metrics_repo import MetricsRepository

pytestmark = pytest.mark.asyncio


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def creator_profile_id() -> UUID:
    return uuid4()


@pytest.fixture
def creator_profile(creator_profile_id: UUID) -> CreatorProfile:
    profile = MagicMock(spec=CreatorProfile)
    profile.id = creator_profile_id
    profile.subscriber_count = 1500
    profile.total_views = 120000
    return profile


def _make_video(
    video_id: UUID,
    duration_seconds: int | None,
) -> MagicMock:
    video = MagicMock()
    video.id = video_id
    video.duration_seconds = duration_seconds
    return video


# ── Repository tests ─────────────────────────────────────────────────────


class TestMetricsRepository:
    """Tests for MetricsRepository persistence."""

    async def test_create_upserts_by_creator_and_timestamp(self) -> None:
        """Creating a snapshot uses upsert on (creator_profile_id, snapshot_at)."""
        db_session = AsyncMock()
        repo = MetricsRepository(db_session)
        profile_id = uuid4()
        now = datetime.now(timezone.utc)

        snapshot = MetricSnapshot(
            id=uuid4(),
            creator_profile_id=profile_id,
            snapshot_at=now,
            total_videos=10,
            total_views=5000,
            total_subscribers=1000,
            avg_views_per_video=500.0,
            avg_view_duration_seconds=300.0,
            total_watch_time_hours=416.67,
            engagement_rate=0.04,
            version=1,
        )

        result = await repo.create(snapshot)

        assert result.id == snapshot.id
        assert result.creator_profile_id == profile_id
        assert result.total_videos == 10
        assert result.engagement_rate == 0.04
        db_session.execute.assert_awaited_once()

    async def test_get_latest_returns_newest_snapshot(self) -> None:
        """get_latest returns the most recent snapshot by snapshot_at."""
        db_session = AsyncMock()
        repo = MetricsRepository(db_session)

        # Mock a scalars().first() result
        mock_result = AsyncMock()
        expected = MagicMock(spec=MetricSnapshot)
        expected.id = uuid4()
        expected.snapshot_at = datetime(2026, 6, 15, tzinfo=timezone.utc)
        mock_result.scalar_one_or_none = AsyncMock(return_value=expected)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_latest(uuid4())
        assert result is not None
        assert result.id == expected.id

    async def test_get_latest_returns_none_for_unknown_creator(self) -> None:
        """get_latest returns None if no snapshots exist."""
        db_session = AsyncMock()
        repo = MetricsRepository(db_session)

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=None)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_latest(uuid4())
        assert result is None


# ── Stage tests ──────────────────────────────────────────────────────────


class TestMetricsCollectionStage:
    """Tests for MetricsCollectionStage."""

    async def test_successful_collection(
        self,
        creator_profile_id: UUID,
        creator_profile: CreatorProfile,
    ) -> None:
        """A successful collection returns a MetricSnapshot with computed values."""
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=creator_profile)

        channel_metrics_repo = AsyncMock()
        channel_metrics_repo.get_latest = AsyncMock(return_value=None)

        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(
            return_value=[
                _make_video(uuid4(), 300),
                _make_video(uuid4(), 600),
                _make_video(uuid4(), 120),
            ]
        )

        captured: list[MetricSnapshot] = []

        async def _create(snapshot: MetricSnapshot) -> MetricSnapshot:
            captured.append(snapshot)
            return snapshot

        metrics_repo = AsyncMock(spec=MetricsRepository)
        metrics_repo.create = AsyncMock(side_effect=_create)

        stage = MetricsCollectionStage(
            creator_profile_repo=profile_repo,
            channel_metrics_repo=channel_metrics_repo,
            video_repo=video_repo,
            metrics_repo=metrics_repo,
        )
        context = MetricsContext(creator_profile_id=creator_profile_id)

        result = await stage.execute(context)

        assert result.total_videos == 3
        assert result.total_subscribers == 1500
        assert result.total_views == 120000
        assert result.avg_views_per_video == 40000.0  # 120000 / 3
        assert result.avg_view_duration_seconds == 340.0  # (300 + 600 + 120) / 3
        assert result.engagement_rate is not None
        assert result.version == 1
        assert len(captured) == 1

    async def test_empty_dataset(
        self,
        creator_profile_id: UUID,
        creator_profile: CreatorProfile,
    ) -> None:
        """A creator with no videos still produces a valid snapshot."""
        creator_profile.total_views = 0
        creator_profile.subscriber_count = 0

        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=creator_profile)

        channel_metrics_repo = AsyncMock()
        channel_metrics_repo.get_latest = AsyncMock(return_value=None)

        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(return_value=[])

        metrics_repo = AsyncMock(spec=MetricsRepository)
        metrics_repo.create = AsyncMock(side_effect=lambda s: s)

        stage = MetricsCollectionStage(
            creator_profile_repo=profile_repo,
            channel_metrics_repo=channel_metrics_repo,
            video_repo=video_repo,
            metrics_repo=metrics_repo,
        )
        context = MetricsContext(creator_profile_id=creator_profile_id)

        result = await stage.execute(context)

        assert result.total_videos == 0
        assert result.total_views == 0
        assert result.total_subscribers == 0
        assert result.avg_views_per_video is None
        assert result.avg_view_duration_seconds is None
        assert result.total_watch_time_hours is None
        assert result.version == 1

    async def test_replay_produces_same_result(
        self,
        creator_profile_id: UUID,
        creator_profile: CreatorProfile,
    ) -> None:
        """Running twice with the same inputs returns equivalent snapshots."""
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=creator_profile)

        channel_metrics_repo = AsyncMock()
        channel_metrics_repo.get_latest = AsyncMock(return_value=None)

        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(
            return_value=[
                _make_video(uuid4(), 300),
            ]
        )

        captured: list[MetricSnapshot] = []

        async def _create(snapshot: MetricSnapshot) -> MetricSnapshot:
            captured.append(snapshot)
            return snapshot

        metrics_repo = AsyncMock(spec=MetricsRepository)
        metrics_repo.create = AsyncMock(side_effect=_create)

        stage = MetricsCollectionStage(
            creator_profile_repo=profile_repo,
            channel_metrics_repo=channel_metrics_repo,
            video_repo=video_repo,
            metrics_repo=metrics_repo,
        )
        context = MetricsContext(creator_profile_id=creator_profile_id)

        snapshot_at = datetime.now(timezone.utc)
        result1 = await stage.execute(context, snapshot_at=snapshot_at)
        result2 = await stage.execute(context, snapshot_at=snapshot_at)

        assert result1.total_videos == result2.total_videos
        assert result1.total_views == result2.total_views
        assert result1.avg_views_per_video == result2.avg_views_per_video
        assert result1.engagement_rate == result2.engagement_rate
        assert result1.version == result2.version

    async def test_historical_snapshots(
        self,
        creator_profile_id: UUID,
        creator_profile: CreatorProfile,
    ) -> None:
        """Each collection creates a separate snapshot, preserving history."""
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=creator_profile)

        channel_metrics_repo = AsyncMock()
        channel_metrics_repo.get_latest = AsyncMock(return_value=None)

        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(
            return_value=[
                _make_video(uuid4(), 300),
            ]
        )

        captured: list[MetricSnapshot] = []

        async def _create(snapshot: MetricSnapshot) -> MetricSnapshot:
            captured.append(snapshot)
            return snapshot

        metrics_repo = AsyncMock(spec=MetricsRepository)
        metrics_repo.create = AsyncMock(side_effect=_create)

        stage = MetricsCollectionStage(
            creator_profile_repo=profile_repo,
            channel_metrics_repo=channel_metrics_repo,
            video_repo=video_repo,
            metrics_repo=metrics_repo,
        )
        context = MetricsContext(creator_profile_id=creator_profile_id)

        for i in range(3):
            t = datetime(2026, 1, 1 + i, tzinfo=timezone.utc)
            await stage.execute(context, snapshot_at=t)

        assert len(captured) == 3
        timestamps = {s.snapshot_at for s in captured}
        assert len(timestamps) == 3

    async def test_incremental_update(
        self,
        creator_profile_id: UUID,
        creator_profile: CreatorProfile,
    ) -> None:
        """New videos since last snapshot are reflected in the next collection."""
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=creator_profile)

        channel_metrics_repo = AsyncMock()
        channel_metrics_repo.get_latest = AsyncMock(return_value=None)

        videos = [
            _make_video(uuid4(), 300),
            _make_video(uuid4(), 600),
        ]
        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(return_value=videos)

        captured: list[MetricSnapshot] = []

        async def _create(snapshot: MetricSnapshot) -> MetricSnapshot:
            captured.append(snapshot)
            return snapshot

        metrics_repo = AsyncMock(spec=MetricsRepository)
        metrics_repo.create = AsyncMock(side_effect=_create)

        stage = MetricsCollectionStage(
            creator_profile_repo=profile_repo,
            channel_metrics_repo=channel_metrics_repo,
            video_repo=video_repo,
            metrics_repo=metrics_repo,
        )
        context = MetricsContext(creator_profile_id=creator_profile_id)

        result1 = await stage.execute(context)
        assert result1.total_videos == 2

        videos.append(_make_video(uuid4(), 120))
        result2 = await stage.execute(context)
        assert result2.total_videos == 3

    async def test_profile_not_found(self, creator_profile_id: UUID) -> None:
        """A missing creator profile raises ValueError."""
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=None)

        channel_metrics_repo = AsyncMock()
        video_repo = AsyncMock()
        metrics_repo = AsyncMock(spec=MetricsRepository)

        stage = MetricsCollectionStage(
            creator_profile_repo=profile_repo,
            channel_metrics_repo=channel_metrics_repo,
            video_repo=video_repo,
            metrics_repo=metrics_repo,
        )
        context = MetricsContext(creator_profile_id=creator_profile_id)

        with pytest.raises(ValueError, match="not found"):
            await stage.execute(context)

    async def test_engagement_rate_from_channel_metrics(
        self,
        creator_profile_id: UUID,
        creator_profile: CreatorProfile,
    ) -> None:
        """Engagement rate uses ChannelMetrics avg_view_duration when available."""
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=creator_profile)

        channel_metrics = MagicMock()
        channel_metrics.avg_view_duration_seconds = 250.0
        channel_metrics_repo = AsyncMock()
        channel_metrics_repo.get_latest = AsyncMock(return_value=channel_metrics)

        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(
            return_value=[
                _make_video(uuid4(), 300),
                _make_video(uuid4(), 600),
            ]
        )

        metrics_repo = AsyncMock(spec=MetricsRepository)
        metrics_repo.create = AsyncMock(side_effect=lambda s: s)

        stage = MetricsCollectionStage(
            creator_profile_repo=profile_repo,
            channel_metrics_repo=channel_metrics_repo,
            video_repo=video_repo,
            metrics_repo=metrics_repo,
        )
        context = MetricsContext(creator_profile_id=creator_profile_id)

        result = await stage.execute(context)

        assert result.total_videos == 2
        assert result.avg_view_duration_seconds is not None
        assert result.engagement_rate is not None
