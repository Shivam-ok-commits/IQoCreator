"""Renders a TitlePatternExtractor pattern into a consultant-style recommendation."""

from __future__ import annotations

from app.intelligence.base import Pattern
from app.pipeline.renderers.base import (
    BaseRenderer,
    build_recommendation_data,
    compute_strength,
)


class TitleRenderer(BaseRenderer):
    """Transforms TitlePattern patterns into specific, evidence-backed recommendations."""

    RANGE_LABELS = {
        "short": "under 30 characters",
        "medium": "30–50 characters",
        "long": "50–70 characters",
        "very_long": "over 70 characters",
    }

    def render(self, pattern: Pattern) -> dict | None:
        best_range = pattern.metrics.get("best_range", "medium")
        best_avg = pattern.metrics.get("best_avg_views", 0)
        worst_avg = pattern.metrics.get("worst_avg_views", 0)

        bins = pattern.evidence.get("title_length_bins", {})
        evidence_lines = []
        total_videos = 0
        for label, data in sorted(bins.items(), key=lambda x: x[1].get("avg_views", 0), reverse=True):
            label_desc = self.RANGE_LABELS.get(label, label)
            count = data.get("count", 0)
            total_videos += count
            evidence_lines.append(
                f"{label_desc}: {data.get('avg_views', 0):,} avg views ({count} videos)"
            )

        if total_videos >= 10 and best_avg > worst_avg * 1.3:
            strength_level = "High"
            strength_rating = 5
        elif total_videos >= 6 and best_avg > worst_avg * 1.2:
            strength_level = "Medium"
            strength_rating = 4
        elif total_videos >= 3:
            strength_level = "Medium"
            strength_rating = 3
        elif total_videos >= 1:
            strength_level = "Low"
            strength_rating = 2
        else:
            strength_level = "Low"
            strength_rating = 1

        best_label_desc = self.RANGE_LABELS.get(best_range, best_range)

        strength = compute_strength(
            level=strength_level,
            rating=strength_rating,
            because=[
                f"{total_videos} total videos analyzed",
                f"Best performers: {best_label_desc} ({best_avg:,} avg views)",
                f"Gap between best and worst titles: {int(best_avg - worst_avg):,} views",
            ],
        )

        top = pattern.evidence.get("top_performing", [])
        top_examples = [f'"{v.get("title", "")}"' for v in top[:2]]

        example_text = ""
        if top_examples:
            example_text = f" For example: {', '.join(top_examples)}."

        action_plan = pattern.suggested_actions or [
            f"Keep your next title to {best_label_desc}",
            "Front-load the most important keyword in the first 5 characters",
            "Test A/B comparing a short and long title for the same topic",
        ]

        supporting_videos = []
        for v in top[:3]:
            supporting_videos.append({
                "title": v.get("title", ""),
                "views": v.get("views", 0),
                "type": "best",
            })

        return build_recommendation_data(
            pattern_type=pattern.type,
            headline=f"Shorter titles perform best — aim for {best_label_desc}",
            observation=(
                f"Videos with {best_label_desc} in the title average "
                f"{best_avg:,} views — significantly higher than longer titles "
                f"which average {worst_avg:,} views.{example_text}"
            ),
            evidence=evidence_lines,
            why_it_matters=(
                "Title length directly impacts click-through rate. "
                "Shorter titles are more scannable, especially on mobile devices "
                "where most YouTube views happen. Every extra word competes for "
                "limited attention."
            ),
            action_plan=action_plan,
            expected_outcome=(
                f"Optimizing title length could improve your click-through rate "
                f"and push average views toward {best_avg:,}"
            ),
            risk_of_doing_nothing=(
                f"If you keep using longer titles, your click-through rate "
                f"will likely stay below what {best_label_desc} titles achieve, "
                f"keeping average views around {worst_avg:,}."
            ),
            strength=strength,
            impact=pattern.impact,
            supporting_videos=supporting_videos,
            why_now=(
                f"Title optimization costs nothing but improves every single "
                f"video going forward — it's the highest-ROI change you can make today."
            ),
        )
