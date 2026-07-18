"""SeriesPatternExtractor — detects sequential video series and compares performance."""

from __future__ import annotations

import re
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.intelligence.base import BaseExtractor, Pattern
from app.models import Video


def _normalise_title(title: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", title.lower()).strip()


def _extract_series_base(title: str) -> str | None:
    """Detect video series patterns like 'Count to 10', 'Count to 20'."""
    t = _normalise_title(title)
    patterns = [
        (r"^(count\s+(to\s+)?\d+)", "count_to"),
        (r"^(learn\s+(to\s+)?\d+)", "learn_numbers"),
        (r"^(number\s+\d+)", "number"),
        (r"^(abc\s)", "abc"),
        (r"^(alphabet\s)", "alphabet"),
        (r"^(phonics\s)", "phonics"),
        (r"^(color\w*\s)", "color"),
        (r"^(colour\w*\s)", "color"),
        (r"^(shape\w*\s)", "shape"),
    ]
    for pattern, series_name in patterns:
        if re.match(pattern, t):
            return series_name
    return None


class SeriesPatternExtractor(BaseExtractor):
    """Detects whether the creator has video series and how they perform vs standalones.

    Series (sequential videos sharing a topic base) typically drive
    higher engagement and watch time than standalone videos.  This
    extractor identifies series and quantifies the performance gap.
    """

    async def extract(
        self,
        creator_profile_id: UUID,
        db: AsyncSession,
    ) -> list[Pattern]:
        result = await db.execute(
            select(Video)
            .options(joinedload(Video.metrics))
            .where(
                Video.creator_profile_id == creator_profile_id,
                Video.is_deleted.is_(False),
            )
        )
        videos = result.unique().scalars().all()
        if len(videos) < 3:
            return []

        series_groups: dict[str, list[Video]] = defaultdict(list)
        standalone: list[Video] = []

        for v in videos:
            base = _extract_series_base(v.title)
            if base:
                series_groups[base].append(v)
            else:
                standalone.append(v)

        patterns = []
        for series_name, group in series_groups.items():
            if len(group) < 2:
                standalone.extend(group)
                continue

            series_views = []
            for v in group:
                if v.metrics:
                    latest = max(v.metrics, key=lambda x: x.recorded_at)
                    series_views.append(latest.view_count or 0)
                else:
                    series_views.append(0)

            series_avg = sum(series_views) / len(series_views) if series_views else 0
            if not series_avg:
                continue

            standalone_views = []
            for v in standalone:
                if v.metrics:
                    latest = max(v.metrics, key=lambda x: x.recorded_at)
                    standalone_views.append(latest.view_count or 0)
                else:
                    standalone_views.append(0)

            standalone_avg = (
                sum(standalone_views) / len(standalone_views)
                if standalone_views
                else 0
            )

            if standalone_avg and series_avg > standalone_avg * 1.5:
                ratio = series_avg / standalone_avg if standalone_avg > 0 else 0
                patterns.append(Pattern(
                    type="series_pattern",
                    summary=f"Your {series_name.replace('_', ' ')} series gets "
                            f"{ratio:.1f}x more views than standalone videos",
                    explanation=(
                        f"Videos in your {series_name.replace('_', ' ')} series "
                        f"({len(group)} videos) average {series_avg:,.0f} views, "
                        f"while your standalone videos average {standalone_avg:,.0f} views. "
                        f"Series build audience expectation and algorithmic momentum."
                    ),
                    confidence=min(0.9, 0.4 + len(group) * 0.08),
                    impact=min(0.9, ratio / 8),
                    metrics={
                        "series_avg_views": round(series_avg),
                        "standalone_avg_views": round(standalone_avg),
                        "ratio": round(ratio, 1),
                        "series_count": len(group),
                        "standalone_count": len(standalone),
                    },
                    evidence={
                        "series": {
                            "name": series_name,
                            "video_count": len(group),
                            "avg_views": round(series_avg),
                            "videos": [
                                {
                                    "title": v.title,
                                    "views": (
                                        max(v.metrics, key=lambda x: x.recorded_at).view_count
                                        if v.metrics else 0
                                    ),
                                }
                                for v in group[:5]
                            ],
                        },
                        "standalone_sample": [
                            {
                                "title": v.title,
                                "views": (
                                    max(v.metrics, key=lambda x: x.recorded_at).view_count
                                    if v.metrics else 0
                                ),
                            }
                            for v in standalone[:3]
                        ],
                    },
                    suggested_actions=[
                        f"Continue your {series_name.replace('_', ' ')} series — "
                        f"it consistently outperforms other content",
                        f"Plan the next 3 videos in this series with a clear progression",
                        f"Add a playlist for the series to increase watch time",
                    ],
                ))

        return patterns
