"""FeatureExtractionStage — derive deterministic channel features from a MetricSnapshot.

This is the second intelligence pipeline stage (Sprint 5B - Phase 5.3).
It consumes one MetricSnapshot and produces one MetricFeatureVector.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.models import MetricFeatureVector, MetricSnapshot, Video
from app.repositories.creator_profile_repo import CreatorProfileRepository
from app.repositories.feature_repo import FeatureRepository
from app.repositories.metrics_repo import MetricsRepository
from app.repositories.video_repo import VideoRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeatureExtractionContext:
    """Immutable context for a feature extraction run.

    Identifies the MetricSnapshot from which features will be derived.
    """

    snapshot_id: UUID


class FeatureExtractionStage:
    """Pipeline stage that derives deterministic features from a MetricSnapshot.

    Responsibilities
    -----------------
    1. Load the MetricSnapshot and its associated creator profile.
    2. Compute deterministic features from snapshot + video data.
    3. Persist an immutable MetricFeatureVector.

    Non-responsibilities
    ---------------------
    - Does not trigger downstream stages.
    - Does not mutate MetricSnapshot or any input artifact.
    - Does not use AI, LLMs, or external APIs.
    """

    FEATURE_SCHEMA_VERSION = 1

    def __init__(
        self,
        *,
        metrics_repo: MetricsRepository,
        creator_profile_repo: CreatorProfileRepository,
        video_repo: VideoRepository,
        feature_repo: FeatureRepository,
    ) -> None:
        self._metrics_repo = metrics_repo
        self._profile_repo = creator_profile_repo
        self._video_repo = video_repo
        self._feature_repo = feature_repo

    async def execute(
        self,
        context: FeatureExtractionContext,
    ) -> MetricFeatureVector:
        """Execute a feature extraction run.

        Parameters
        ----------
        context : FeatureExtractionContext
            Identifies the MetricSnapshot to extract features from.

        Returns
        -------
        MetricFeatureVector
            The persisted feature vector artifact.

        Raises
        ------
        ValueError
            If the MetricSnapshot does not exist.
        """
        # ── 1. Load the snapshot ─────────────────────────────────────
        snapshot = await self._metrics_repo.get_by_id(context.snapshot_id)
        if snapshot is None:
            raise ValueError(
                f"MetricSnapshot {context.snapshot_id} not found"
            )

        # ── 2. Load creator profile ──────────────────────────────────
        profile = await self._profile_repo.get_by_id(
            snapshot.creator_profile_id
        )
        channel_age_days: float | None = None
        if profile and profile.joined_platform_at and snapshot.snapshot_at:
            delta = snapshot.snapshot_at - profile.joined_platform_at
            channel_age_days = round(delta.total_seconds() / 86400, 2)

        # ── 3. Load videos for per-video features ────────────────────
        videos = await self._video_repo.get_by_creator_profile(
            snapshot.creator_profile_id
        )
        total_videos_count = snapshot.total_videos or len(videos)

        # ── 4. Compute features ──────────────────────────────────────
        features: dict[str, float | int | str | None] = {}

        # total_videos
        features["total_videos"] = total_videos_count

        # upload_frequency (videos per day since channel creation)
        if channel_age_days and channel_age_days > 0:
            features["upload_frequency"] = round(
                total_videos_count / channel_age_days, 4
            )
        else:
            features["upload_frequency"] = None

        # average_views
        features["average_views"] = snapshot.avg_views_per_video

        # average_likes — estimated from channel-level data
        # Without per-video metrics, we estimate from engagement_rate * average_views
        avg_likes: float | int | None = None
        if snapshot.engagement_rate and snapshot.avg_views_per_video:
            # engagement_rate = (likes + comments) / views
            # Rough split: ~80% likes, ~20% comments of total engagement
            avg_likes = round(
                snapshot.avg_views_per_video * snapshot.engagement_rate * 0.8, 2
            )
        features["average_likes"] = avg_likes

        # average_comments
        avg_comments: float | int | None = None
        if snapshot.engagement_rate and snapshot.avg_views_per_video:
            avg_comments = round(
                snapshot.avg_views_per_video * snapshot.engagement_rate * 0.2, 2
            )
        features["average_comments"] = avg_comments

        # engagement_rate
        features["engagement_rate"] = snapshot.engagement_rate

        # shorts_ratio (videos < 60s / total)
        if videos:
            short_count = sum(
                1 for v in videos if v.duration_seconds is not None and v.duration_seconds < 60
            )
            features["shorts_ratio"] = round(short_count / len(videos), 4)
        else:
            features["shorts_ratio"] = None

        # average_duration
        features["average_duration"] = snapshot.avg_view_duration_seconds

        # average_title_length
        if videos:
            title_lengths = [
                len(v.title) for v in videos if v.title
            ]
            if title_lengths:
                features["average_title_length"] = round(
                    sum(title_lengths) / len(title_lengths), 2
                )
            else:
                features["average_title_length"] = None
        else:
            features["average_title_length"] = None

        # channel_age_days
        features["channel_age_days"] = channel_age_days

        # ── 5. Create and persist vector ─────────────────────────────
        vector = MetricFeatureVector(
            id=uuid4(),
            creator_profile_id=snapshot.creator_profile_id,
            source_snapshot_id=snapshot.id,
            features=features,
            feature_schema_version=self.FEATURE_SCHEMA_VERSION,
            version=1,
        )

        persisted = await self._feature_repo.create(vector)
        logger.info(
            "Created MetricFeatureVector %s from snapshot %s (%d features)",
            persisted.id,
            context.snapshot_id,
            len(features),
        )
        return persisted
