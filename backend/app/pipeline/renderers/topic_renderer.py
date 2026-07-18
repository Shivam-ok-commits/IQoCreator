"""Renders a TopicClusterExtractor pattern into a consultant-style recommendation."""

from __future__ import annotations

from app.intelligence.base import Pattern
from app.pipeline.renderers.base import (
    BaseRenderer,
    build_recommendation_data,
    compute_strength,
)


class TopicRenderer(BaseRenderer):
    """Transforms TopicCluster patterns into specific, evidence-backed recommendations."""

    def render(self, pattern: Pattern) -> dict | None:
        best_name = pattern.metrics.get("best_cluster_name", "")
        best_avg = pattern.metrics.get(f"{best_name}_avg_views", 0)
        worst_name = pattern.metrics.get("worst_cluster_name", "")
        worst_avg = pattern.metrics.get(f"{worst_name}_avg_views", 0)
        ratio = pattern.metrics.get("ratio", 1.0)

        best_cluster = pattern.evidence.get("best_cluster", {})
        worst_cluster = pattern.evidence.get("worst_cluster", {})

        best_count = best_cluster.get("video_count", 0)
        worst_count = worst_cluster.get("video_count", 0)

        evidence_lines = [
            f"{best_count} {best_name} videos averaged {best_avg:,} views",
            f"{worst_count} {worst_name} videos averaged {worst_avg:,} views",
        ]

        total = best_count + worst_count
        if total >= 8:
            strength_level = "High"
            strength_rating = 5
        elif total >= 5:
            strength_level = "Medium"
            strength_rating = 4
        elif total >= 3:
            strength_level = "Medium"
            strength_rating = 3
        elif total >= 1:
            strength_level = "Low"
            strength_rating = 2
        else:
            strength_level = "Low"
            strength_rating = 1

        strength = compute_strength(
            level=strength_level,
            rating=strength_rating,
            because=[
                f"{best_count} {best_name} videos compared against {worst_count} {worst_name} videos",
                f"{ratio:.1f}x performance gap",
                "Consistent trend across your upload history",
            ],
        )

        potential = int(best_avg * (1 + pattern.impact * 0.5))

        action_plan = pattern.suggested_actions or [
            f"Publish 3 more {best_name} videos before your next {worst_name} video",
            f"Analyze what makes your top {best_name} videos work and replicate it",
            f"Create a playlist organizing your {best_name} content",
        ]

        video_ids = []
        supporting_videos = []
        for v in best_cluster.get("sample", []):
            if isinstance(v, dict):
                if "platform_video_id" in v:
                    video_ids.append(v["platform_video_id"])
                supporting_videos.append({
                    "title": v.get("title", ""),
                    "views": v.get("views", 0),
                    "type": "best",
                })
        for v in worst_cluster.get("sample", []):
            if isinstance(v, dict):
                supporting_videos.append({
                    "title": v.get("title", ""),
                    "views": v.get("views", 0),
                    "type": "worst",
                })

        return build_recommendation_data(
            pattern_type=pattern.type,
            headline=f"Double down on your {best_name} content — it outperforms everything else",
            observation=(
                f"Your {best_name} videos consistently outperform {worst_name} videos "
                f"by {ratio:.1f}x. This pattern holds across {best_count} uploads."
            ),
            evidence=evidence_lines,
            why_it_matters=(
                f"Your audience has shown a clear preference for {best_name} content. "
                f"Publishing {worst_name} videos in between resets the momentum "
                f"your best content builds."
            ),
            action_plan=action_plan,
            expected_outcome=(
                f"If you focus your next uploads on {best_name} content, "
                f"your average views could grow from {worst_avg:,} to "
                f"{best_avg:,}–{potential:,}"
            ),
            risk_of_doing_nothing=(
                f"Your next videos will likely land between {worst_avg:,} and "
                f"{best_avg:,} views, because underperforming topics "
                f"will continue to pull your channel average down."
            ),
            strength=strength,
            impact=pattern.impact,
            supporting_video_ids=video_ids,
            supporting_videos=supporting_videos,
            why_now=(
                f"Improving topic selection affects every future upload, "
                f"making it the highest-leverage change available today."
            ),
        )
