"""TopicClusterExtractor — groups videos by topic keyword clusters and compares performance."""

from __future__ import annotations

import re
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.intelligence.base import BaseExtractor, Pattern
from app.models import Video, VideoMetrics

STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
    "of", "with", "is", "it", "by", "from", "be", "this", "that",
    "song", "video", "new", "learn", "fun", "kids", "for", "and",
})


def _extract_keywords(title: str) -> frozenset[str]:
    words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()
    return frozenset(w for w in words if w not in STOP_WORDS and len(w) > 2)


def _cluster_videos(
    videos: list[tuple[Video, dict]],
) -> dict[str, list[tuple[Video, dict]]]:
    clusters: dict[str, list[tuple[Video, dict]]] = defaultdict(list)
    for v, m in videos:
        title_lower = v.title.lower()
        for topic in ("count", "number", "counting", "1", "2", "3"):
            if topic in title_lower:
                clusters["counting"].append((v, m))
                break
        else:
            for topic in ("shape", "circle", "square", "triangle", "diamond"):
                if topic in title_lower:
                    clusters["shapes"].append((v, m))
                    break
            else:
                for topic in ("color", "colour", "red", "blue", "green", "yellow"):
                    if topic in title_lower:
                        clusters["colors"].append((v, m))
                        break
                else:
                    for topic in ("abc", "alphabet", "letter", "phonics"):
                        if topic in title_lower:
                            clusters["alphabet"].append((v, m))
                            break
                    else:
                        clusters["other"].append((v, m))

    return {k: v for k, v in clusters.items() if len(v) >= 2}


class TopicClusterExtractor(BaseExtractor):
    """Detects topic-based performance differences across a creator's videos.

    Groups videos by detected topic keywords, compares average view counts
    per cluster, and returns a pattern highlighting the best-performing
    topic when there is a meaningful gap.
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
        if len(videos) < 4:
            return []

        video_with_metrics: list[tuple[Video, dict]] = []
        for v in videos:
            m = {}
            if v.metrics:
                latest = max(v.metrics, key=lambda x: x.recorded_at)
                m = {
                    "view_count": latest.view_count or 0,
                    "like_count": latest.like_count or 0,
                }
            video_with_metrics.append((v, m))

        clusters = _cluster_videos(video_with_metrics)
        if len(clusters) < 2:
            return []

        cluster_stats = {}
        for name, group in clusters.items():
            views = [m.get("view_count", 0) for _, m in group]
            avg = sum(views) / len(views) if views else 0
            cluster_stats[name] = {
                "count": len(group),
                "avg_views": round(avg),
                "videos": [
                    {"title": v.title, "views": m.get("view_count", 0)}
                    for v, m in group[:5]
                ],
            }

        sorted_clusters = sorted(
            cluster_stats.items(), key=lambda x: x[1]["avg_views"], reverse=True
        )
        best_name, best = sorted_clusters[0]
        worst_name, worst = sorted_clusters[-1]

        if best["avg_views"] <= worst["avg_views"] * 1.5:
            return []

        ratio = best["avg_views"] / worst["avg_views"] if worst["avg_views"] > 0 else 0
        n = min(len(sorted_clusters), 3)

        patterns = []
        for i in range(n - 1):
            higher = sorted_clusters[i]
            lower = sorted_clusters[i + 1]
            if higher[1]["avg_views"] <= lower[1]["avg_views"] * 1.5:
                continue

            gap_ratio = higher[1]["avg_views"] / lower[1]["avg_views"] if lower[1]["avg_views"] > 0 else 0
            patterns.append(Pattern(
                type="topic_cluster",
                summary=f"{higher[0].title()} videos outperform {lower[0]} videos "
                        f"by {gap_ratio:.1f}x",
                explanation=(
                    f"Your {higher[0]} videos average {higher[1]['avg_views']:,} views "
                    f"({higher[1]['count']} videos), while your {lower[0]} videos "
                    f"average {lower[1]['avg_views']:,} views ({lower[1]['count']} videos). "
                    f"This suggests your audience strongly prefers {higher[0]} content."
                ),
                confidence=min(0.95, 0.5 + higher[1]["count"] * 0.05),
                impact=min(0.95, gap_ratio / 10),
                metrics={
                    f"{higher[0]}_avg_views": higher[1]["avg_views"],
                    f"{lower[0]}_avg_views": lower[1]["avg_views"],
                    "ratio": round(gap_ratio, 1),
                },
                evidence={
                    "best_cluster": {
                        "name": higher[0],
                        "video_count": higher[1]["count"],
                        "avg_views": higher[1]["avg_views"],
                        "sample": higher[1]["videos"],
                    },
                    "worst_cluster": {
                        "name": lower[0],
                        "video_count": lower[1]["count"],
                        "avg_views": lower[1]["avg_views"],
                        "sample": lower[1]["videos"],
                    },
                },
                suggested_actions=[
                    f"Create more {higher[0]} content — it gets {gap_ratio:.1f}x more views",
                    f"Reduce or rethink your {lower[0]} content strategy",
                    f"Test combining {higher[0]} themes with other topics to expand your reach",
                ],
            ))

        return patterns
