"""TitlePatternExtractor — analyzes title length vs performance correlation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.intelligence.base import BaseExtractor, Pattern
from app.models import Video


class TitlePatternExtractor(BaseExtractor):
    """Correlates video title length with view performance.

    Groups videos by title character length bins and identifies
    the optimal length range for the creator's audience.
    """

    BINS = [
        (0, 30, "short"),
        (30, 50, "medium"),
        (50, 70, "long"),
        (70, 200, "very_long"),
    ]

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
        if len(videos) < 4:
            return []

        bins: dict[str, list[dict]] = {label: [] for _, _, label in self.BINS}
        for v in videos:
            length = len(v.title)
            view_count = 0
            if v.metrics:
                latest = max(v.metrics, key=lambda x: x.recorded_at)
                view_count = latest.view_count or 0
            for lo, hi, label in self.BINS:
                if lo <= length < hi:
                    bins[label].append({
                        "title": v.title,
                        "length": length,
                        "views": view_count,
                    })
                    break

        stats = {}
        for label, group in bins.items():
            if len(group) < 2:
                continue
            views = [v["views"] for v in group]
            avg = sum(views) / len(views) if views else 0
            stats[label] = {
                "count": len(group),
                "avg_views": round(avg),
            }

        if len(stats) < 2:
            return []

        sorted_bins = sorted(
            stats.items(), key=lambda x: x[1]["avg_views"], reverse=True
        )
        best_label, best = sorted_bins[0]
        worst_label, worst = sorted_bins[-1]

        if best["avg_views"] <= worst["avg_views"] * 1.3:
            return []

        range_labels = {
            "short": "under 30 characters",
            "medium": "30–50 characters",
            "long": "50–70 characters",
            "very_long": "over 70 characters",
        }

        patterns = []
        for label, bin_data in sorted_bins[:1]:
            label_desc = range_labels.get(label, label)
            patterns.append(Pattern(
                type="title_pattern",
                summary=f"Titles with {label_desc} perform best",
                explanation=(
                    f"Videos with {label_desc} in their title average "
                    f"{bin_data['avg_views']:,} views ({bin_data['count']} videos). "
                    f"Shorter titles are more scannable and create curiosity."
                ),
                confidence=min(0.85, 0.4 + bin_data["count"] * 0.05),
                impact=min(0.7, (best["avg_views"] - worst["avg_views"])
                          / max(best["avg_views"], 1) * 0.5),
                metrics={
                    "best_range": label,
                    "best_avg_views": best["avg_views"],
                    "worst_range": worst_label if worst["avg_views"] > 0 else label,
                    "worst_avg_views": worst["avg_views"],
                    "total_videos_analyzed": len(videos),
                },
                evidence={
                    "title_length_bins": {
                        k: {
                            "count": v["count"],
                            "avg_views": v["avg_views"],
                        }
                        for k, v in stats.items()
                    },
                    "top_performing": [
                        v for v in bins[best_label][:3]
                    ],
                },
                suggested_actions=[
                    f"Aim for {label_desc} in your next title",
                    "Lead with the most important words first",
                    "Test shorter titles against your current style",
                ],
            ))

        return patterns
