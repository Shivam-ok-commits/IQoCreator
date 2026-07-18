"""Renders a SeriesPatternExtractor pattern into a consultant-style recommendation."""

from __future__ import annotations

from app.intelligence.base import Pattern
from app.pipeline.renderers.base import (
    BaseRenderer,
    build_recommendation_data,
    compute_strength,
)


class SeriesRenderer(BaseRenderer):
    """Transforms SeriesPattern patterns into specific, evidence-backed recommendations."""

    def render(self, pattern: Pattern) -> dict | None:
        series_name = pattern.metrics.get("series_name", "this series")
        series_avg = pattern.metrics.get("series_avg_views", 0)
        standalone_avg = pattern.metrics.get("standalone_avg_views", 0)
        ratio = pattern.metrics.get("ratio", 1.0)
        series_count = pattern.metrics.get("series_count", 0)
        standalone_count = pattern.metrics.get("standalone_count", 0)

        series_evidence = pattern.evidence.get("series", {})
        standalone_sample = pattern.evidence.get("standalone_sample", [])

        evidence_lines = [
            f"{series_count} videos in the {series_name} series averaged {series_avg:,} views",
            f"{standalone_count} standalone videos averaged {standalone_avg:,} views",
        ]

        total = series_count + standalone_count
        if total >= 8 and ratio >= 1.5:
            strength_level = "High"
            strength_rating = 5
        elif total >= 5 and ratio >= 1.3:
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
                f"{series_count} videos in the series",
                f"{standalone_count} standalone videos for comparison",
                f"{ratio:.1f}x performance advantage over standalone content",
            ],
        )

        potential = int(standalone_avg * ratio) if standalone_avg else int(series_avg * 1.3)

        action_plan = pattern.suggested_actions or [
            f"Plan and publish the next 3 videos in your {series_name} series",
            f"Create a dedicated playlist so viewers can binge the series",
            f"Reference the series in your video descriptions to cross-link content",
        ]

        video_ids = []
        supporting_videos = []
        for v in series_evidence.get("videos", []):
            if isinstance(v, dict):
                if "platform_video_id" in v:
                    video_ids.append(v["platform_video_id"])
                supporting_videos.append({
                    "title": v.get("title", ""),
                    "views": v.get("views", 0),
                    "type": "series",
                })

        return build_recommendation_data(
            pattern_type=pattern.type,
            headline=f"Keep building your {series_name} series — it drives {ratio:.1f}x more views",
            observation=(
                f"Your {series_name} series ({series_count} videos) averages "
                f"{series_avg:,} views — {ratio:.1f}x higher than your standalone "
                f"content ({standalone_avg:,} views)."
            ),
            evidence=evidence_lines,
            why_it_matters=(
                f"Series build audience expectation and algorithmic momentum. "
                f"Viewers who watch one video in a series are far more likely "
                f"to watch the next, increasing both watch time and session duration."
            ),
            action_plan=action_plan,
            expected_outcome=(
                f"Continuing this series could grow your average from "
                f"{standalone_avg:,} to {potential:,} views per video"
            ),
            risk_of_doing_nothing=(
                f"Without building this series further, your channel averages "
                f"{standalone_avg:,} views — the series is your best path "
                f"to consistent view growth."
            ),
            strength=strength,
            impact=pattern.impact,
            supporting_video_ids=video_ids,
            supporting_videos=supporting_videos,
            why_now=(
                f"Building a serialized format compounds with every new episode, "
                f"creating habitual viewers who return for each installment."
            ),
        )
