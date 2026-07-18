"""Tests for FeatureExtractionStage and FeatureRepository.

Covers: successful extraction, empty snapshot, replay/idempotency,
historical persistence, incremental snapshots, repository queries,
feature values verified against known inputs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models import CreatorProfile, MetricFeatureVector, MetricSnapshot
from app.pipeline.feature_extraction_stage import (
    FeatureExtractionContext,
    FeatureExtractionStage,
)
from app.repositories.feature_repo import FeatureRepository

pytestmark = pytest.mark.asyncio


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def creator_profile_id() -> UUID:
    return uuid4()


@pytest.fixture
def snapshot_id() -> UUID:
    return uuid4()


def _make_snapshot(
    snapshot_id: UUID,
    creator_profile_id: UUID,
    *,
    total_videos: int = 10,
    total_views: int = 50000,
    total_subscribers: int = 1500,
    avg_views_per_video: float = 5000.0,
    avg_view_duration_seconds: float = 340.0,
    total_watch_time_hours: float = 4166.67,
    engagement_rate: float = 0.04,
) -> MetricSnapshot:
    snapshot = MagicMock(spec=MetricSnapshot)
    snapshot.id = snapshot_id
    snapshot.creator_profile_id = creator_profile_id
    snapshot.total_videos = total_videos
    snapshot.total_views = total_views
    snapshot.total_subscribers = total_subscribers
    snapshot.avg_views_per_video = avg_views_per_video
    snapshot.avg_view_duration_seconds = avg_view_duration_seconds
    snapshot.total_watch_time_hours = total_watch_time_hours
    snapshot.engagement_rate = engagement_rate
    return snapshot


def _make_video(
    video_id: UUID,
    title: str = "Test Video",
    duration_seconds: int = 300,
) -> MagicMock:
    video = MagicMock()
    video.id = video_id
    video.title = title
    video.duration_seconds = duration_seconds
    return video


# ── Repository tests ─────────────────────────────────────────────────────


class TestFeatureRepository:
    """Tests for FeatureRepository persistence."""

    async def test_create_and_retrieve(self) -> None:
        """A created feature vector can be retrieved by ID."""
        db_session = AsyncMock()
        repo = FeatureRepository(db_session)
        vector_id = uuid4()
        profile_id = uuid4()
        snapshot_id_val = uuid4()

        vector = MetricFeatureVector(
            id=vector_id,
            creator_profile_id=profile_id,
            source_snapshot_id=snapshot_id_val,
            features={"total_videos": 10, "engagement_rate": 0.04},
            feature_schema_version=1,
            version=1,
        )

        result = await repo.create(vector)
        assert result.id == vector_id
        assert result.source_snapshot_id == snapshot_id_val
        assert result.features["total_videos"] == 10
        db_session.execute.assert_awaited_once()

    async def test_get_by_snapshot_returns_matching_vector(self) -> None:
        """get_by_snapshot returns the vector for a given snapshot."""
        db_session = AsyncMock()
        repo = FeatureRepository(db_session)
        snapshot_id_val = uuid4()

        mock_result = AsyncMock()
        expected = MagicMock(spec=MetricFeatureVector)
        expected.source_snapshot_id = snapshot_id_val
        mock_result.scalar_one_or_none = AsyncMock(return_value=expected)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_snapshot(snapshot_id_val)
        assert result is not None
        assert result.source_snapshot_id == snapshot_id_val

    async def test_get_latest_returns_most_recent(self) -> None:
        """get_latest_by_creator returns the newest feature vector."""
        db_session = AsyncMock()
        repo = FeatureRepository(db_session)

        mock_result = AsyncMock()
        expected = MagicMock(spec=MetricFeatureVector)
        expected.id = uuid4()
        mock_result.scalar_one_or_none = AsyncMock(return_value=expected)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_latest_by_creator(uuid4())
        assert result is not None
        assert result.id == expected.id


# ── Stage tests ──────────────────────────────────────────────────────────


class TestFeatureExtractionStage:
    """Tests for FeatureExtractionStage."""

    async def test_successful_extraction(
        self,
        creator_profile_id: UUID,
        snapshot_id: UUID,
    ) -> None:
        """A valid snapshot produces a MetricFeatureVector with all expected features."""
        snapshot = _make_snapshot(snapshot_id, creator_profile_id)

        metrics_repo = AsyncMock()
        metrics_repo.get_by_id = AsyncMock(return_value=snapshot)

        profile = MagicMock(spec=CreatorProfile)
        profile.joined_platform_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=profile)

        videos = [
            _make_video(uuid4(), "Long Title Video", 300),
            _make_video(uuid4(), "Short", 45),
            _make_video(uuid4(), "Another Video", 600),
        ]
        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(return_value=videos)

        captured: list[MetricFeatureVector] = []

        async def _create(v: MetricFeatureVector) -> MetricFeatureVector:
            captured.append(v)
            return v

        feature_repo = AsyncMock(spec=FeatureRepository)
        feature_repo.create = AsyncMock(side_effect=_create)

        stage = FeatureExtractionStage(
            metrics_repo=metrics_repo,
            creator_profile_repo=profile_repo,
            video_repo=video_repo,
            feature_repo=feature_repo,
        )
        context = FeatureExtractionContext(snapshot_id=snapshot_id)

        result = await stage.execute(context)

        # Verify all expected features are present
        assert "total_videos" in result.features
        assert "upload_frequency" in result.features
        assert "average_views" in result.features
        assert "average_likes" in result.features
        assert "average_comments" in result.features
        assert "engagement_rate" in result.features
        assert "shorts_ratio" in result.features
        assert "average_duration" in result.features
        assert "average_title_length" in result.features
        assert "channel_age_days" in result.features

        # Verify specific values
        assert result.features["total_videos"] == 10
        assert result.features["average_views"] == 5000.0
        assert result.features["engagement_rate"] == 0.04
        # 1 short out of 3 videos
        assert result.features["shorts_ratio"] == pytest.approx(1 / 3, rel=0.01)
        # Title lengths: "Long Title Video" (16) + "Short" (5) + "Another Video" (13) = 34 / 3 = 11.33
        assert result.features["average_title_length"] == pytest.approx(11.33, rel=0.1)
        # duration = 340.0
        assert result.features["average_duration"] == 340.0
        # channel age > 0
        assert result.features["channel_age_days"] is not None
        assert float(result.features["channel_age_days"]) > 0  # type: ignore[arg-type]
        # upload frequency: 10 videos / channel_age_days
        assert result.features["upload_frequency"] is not None
        assert float(result.features["upload_frequency"]) > 0  # type: ignore[arg-type]

        assert result.source_snapshot_id == snapshot_id
        assert result.feature_schema_version == 1
        assert result.version == 1
        assert len(captured) == 1

    async def test_replay_produces_same_features(
        self,
        creator_profile_id: UUID,
        snapshot_id: UUID,
    ) -> None:
        """Running twice with the same snapshot returns identical features."""
        snapshot = _make_snapshot(snapshot_id, creator_profile_id)

        metrics_repo = AsyncMock()
        metrics_repo.get_by_id = AsyncMock(return_value=snapshot)

        profile = MagicMock(spec=CreatorProfile)
        profile.joined_platform_at = datetime(2023, 6, 15, tzinfo=timezone.utc)
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=profile)

        videos = [
            _make_video(uuid4(), "Video A", 300),
            _make_video(uuid4(), "Video B", 600),
        ]
        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(return_value=videos)

        captured: list[MetricFeatureVector] = []

        async def _create(v: MetricFeatureVector) -> MetricFeatureVector:
            captured.append(v)
            return v

        feature_repo = AsyncMock(spec=FeatureRepository)
        feature_repo.create = AsyncMock(side_effect=_create)

        stage = FeatureExtractionStage(
            metrics_repo=metrics_repo,
            creator_profile_repo=profile_repo,
            video_repo=video_repo,
            feature_repo=feature_repo,
        )
        context = FeatureExtractionContext(snapshot_id=snapshot_id)

        result1 = await stage.execute(context)
        result2 = await stage.execute(context)

        # Same features (excluding ID which is new per run)
        for key in result1.features:
            assert result1.features[key] == result2.features[key], (
                f"Feature '{key}' differs on replay: "
                f"{result1.features[key]} != {result2.features[key]}"
            )

    async def test_empty_metrics_snapshot(
        self,
        creator_profile_id: UUID,
        snapshot_id: UUID,
    ) -> None:
        """A snapshot with no videos still produces a valid feature vector."""
        snapshot = _make_snapshot(
            snapshot_id, creator_profile_id,
            total_videos=0, total_views=0,
            total_subscribers=0, avg_views_per_video=None,
            avg_view_duration_seconds=None, total_watch_time_hours=None,
            engagement_rate=None,
        )

        metrics_repo = AsyncMock()
        metrics_repo.get_by_id = AsyncMock(return_value=snapshot)

        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=None)

        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(return_value=[])

        feature_repo = AsyncMock(spec=FeatureRepository)
        feature_repo.create = AsyncMock(side_effect=lambda v: v)

        stage = FeatureExtractionStage(
            metrics_repo=metrics_repo,
            creator_profile_repo=profile_repo,
            video_repo=video_repo,
            feature_repo=feature_repo,
        )
        context = FeatureExtractionContext(snapshot_id=snapshot_id)

        result = await stage.execute(context)

        assert result.features["total_videos"] == 0
        assert result.features["average_views"] is None
        assert result.features["engagement_rate"] is None
        assert result.features["shorts_ratio"] is None
        assert result.features["average_title_length"] is None
        assert result.features["channel_age_days"] is None
        assert result.features["upload_frequency"] is None
        assert result.feature_schema_version == 1

    async def test_snapshot_not_found(self, snapshot_id: UUID) -> None:
        """A missing snapshot raises ValueError."""
        metrics_repo = AsyncMock()
        metrics_repo.get_by_id = AsyncMock(return_value=None)

        profile_repo = AsyncMock()
        video_repo = AsyncMock()
        feature_repo = AsyncMock(spec=FeatureRepository)

        stage = FeatureExtractionStage(
            metrics_repo=metrics_repo,
            creator_profile_repo=profile_repo,
            video_repo=video_repo,
            feature_repo=feature_repo,
        )
        context = FeatureExtractionContext(snapshot_id=snapshot_id)

        with pytest.raises(ValueError, match="not found"):
            await stage.execute(context)

    async def test_incremental_snapshot_produces_new_vector(
        self,
        creator_profile_id: UUID,
    ) -> None:
        """Two different MetricSnapshots produce two separate feature vectors."""
        snapshot_1 = _make_snapshot(uuid4(), creator_profile_id, total_videos=5)
        snapshot_2 = _make_snapshot(uuid4(), creator_profile_id, total_videos=10)

        metrics_repo = AsyncMock()
        metrics_repo.get_by_id = AsyncMock(side_effect=lambda id: (
            snapshot_1 if id == snapshot_1.id else snapshot_2
        ))

        profile = MagicMock(spec=CreatorProfile)
        profile.joined_platform_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=profile)

        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(
            return_value=[_make_video(uuid4(), "V", 300)]
        )

        created: list[MetricFeatureVector] = []

        async def _create(v: MetricFeatureVector) -> MetricFeatureVector:
            created.append(v)
            return v

        feature_repo = AsyncMock(spec=FeatureRepository)
        feature_repo.create = AsyncMock(side_effect=_create)

        stage = FeatureExtractionStage(
            metrics_repo=metrics_repo,
            creator_profile_repo=profile_repo,
            video_repo=video_repo,
            feature_repo=feature_repo,
        )

        ctx_1 = FeatureExtractionContext(snapshot_id=snapshot_1.id)
        ctx_2 = FeatureExtractionContext(snapshot_id=snapshot_2.id)

        result_1 = await stage.execute(ctx_1)
        result_2 = await stage.execute(ctx_2)

        assert result_1.source_snapshot_id == snapshot_1.id
        assert result_2.source_snapshot_id == snapshot_2.id
        assert result_1.id != result_2.id
        assert result_1.features["total_videos"] == 5
        assert result_2.features["total_videos"] == 10
        assert len(created) == 2

    async def test_feature_values_verified_against_known_inputs(
        self,
        creator_profile_id: UUID,
    ) -> None:
        """Feature values are deterministic and match expectations."""
        snapshot_id_val = uuid4()
        snapshot = _make_snapshot(
            snapshot_id_val, creator_profile_id,
            total_videos=20,
            total_views=100000,
            avg_views_per_video=5000.0,
            avg_view_duration_seconds=450.0,
            engagement_rate=0.05,
        )

        metrics_repo = AsyncMock()
        metrics_repo.get_by_id = AsyncMock(return_value=snapshot)

        profile = MagicMock(spec=CreatorProfile)
        profile.joined_platform_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=profile)

        # 20 videos: 5 shorts (<60s), 15 long
        videos = [_make_video(uuid4(), "Short", 30) for _ in range(5)]
        videos += [_make_video(uuid4(), "Long Video Title Here", 450) for _ in range(15)]
        video_repo = AsyncMock()
        video_repo.get_by_creator_profile = AsyncMock(return_value=videos)

        feature_repo = AsyncMock(spec=FeatureRepository)
        feature_repo.create = AsyncMock(side_effect=lambda v: v)

        stage = FeatureExtractionStage(
            metrics_repo=metrics_repo,
            creator_profile_repo=profile_repo,
            video_repo=video_repo,
            feature_repo=feature_repo,
        )
        context = FeatureExtractionContext(snapshot_id=snapshot_id_val)

        result = await stage.execute(context)

        # Verify known values
        assert result.features["total_videos"] == 20
        assert result.features["average_views"] == 5000.0
        # engagement_rate * avg_views * 0.8 = 5000 * 0.05 * 0.8 = 200
        assert result.features["average_likes"] == 200.0
        # engagement_rate * avg_views * 0.2 = 5000 * 0.05 * 0.2 = 50
        assert result.features["average_comments"] == 50.0
        assert result.features["engagement_rate"] == 0.05
        # 5 shorts / 20 total = 0.25
        assert result.features["shorts_ratio"] == 0.25
        assert result.features["average_duration"] == 450.0
        # Title lengths: 5 * 5 ("Short") + 15 * 21 ("Long Video Title Here") = 25 + 315 = 340 / 20 = 17.0
        assert result.features["average_title_length"] == 17.0
