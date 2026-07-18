"""ReportGenerator — produces an ExecutiveSummary after recommendations are generated.

Runs as the terminal pipeline stage.  Consumes intelligence patterns and
pipeline recommendations and writes a channel-level narrative that frames
everything underneath as supporting evidence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.base import Pattern
from app.models import ChannelReport, PipelineRecommendation, Video
from app.repositories.recommendation_repo import RecommendationRepository

logger = logging.getLogger(__name__)


@dataclass
class ReportContext:
    """Context for the report generator stage."""

    creator_profile_id: UUID
    analysis_run_id: UUID | None = None
    patterns: tuple[Pattern, ...] = field(default_factory=tuple)
    recommendations: tuple[PipelineRecommendation, ...] = field(default_factory=tuple)


@dataclass
class ExecutiveSummary:
    """The narrative executive summary output."""

    version: int = 1
    thesis: str = ""
    biggest_opportunity: str = ""
    biggest_risk: str = ""
    what_surprised_us: str | None = None
    next_30_day_goal: str = ""
    channel_story: str | None = None
    recommendation_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "thesis": self.thesis,
            "biggest_opportunity": self.biggest_opportunity,
            "biggest_risk": self.biggest_risk,
            "what_surprised_us": self.what_surprised_us,
            "next_30_day_goal": self.next_30_day_goal,
            "channel_story": self.channel_story,
            "recommendation_ids": self.recommendation_ids,
        }


async def generate_report(
    context: ReportContext,
    db: AsyncSession,
) -> ExecutiveSummary | None:
    """Generate an ExecutiveSummary for the completed analysis run.

    Returns None if there's insufficient data to build a meaningful report.
    """
    if not context.patterns and not context.recommendations:
        return None

    top_pattern = context.patterns[0] if context.patterns else None
    all_recs = context.recommendations

    # ── Total videos & time span ──────────────────────────────────────
    total_videos = 0
    months_span = 0
    try:
        row = await db.execute(
            select(
                sa_func.count(Video.id),
                sa_func.min(Video.published_at),
                sa_func.max(Video.published_at),
            ).where(Video.creator_profile_id == context.creator_profile_id)
        )
        count, min_ts, max_ts = row.one()
        total_videos = count or 0
        if min_ts and max_ts:
            delta = max_ts - min_ts
            months_span = max(1, round(delta.days / 30))
    except Exception:
        logger.warning("Could not determine video stats for report", exc_info=True)

    # ── Derive narrative fields from top pattern ──────────────────────
    thesis = _build_thesis(top_pattern, total_videos, months_span)
    channel_story = _build_channel_story(top_pattern, total_videos, months_span)
    biggest_risk = _build_biggest_risk(top_pattern, all_recs)
    what_surprised_us = _build_surprise(top_pattern, context.patterns)

    # ── Next 30 day goal ──────────────────────────────────────────────
    next_30_day_goal = ""
    if top_pattern and top_pattern.suggested_actions:
        first = top_pattern.suggested_actions[0]
        next_30_day_goal = f"{first}"
    elif all_recs:
        d = all_recs[0].details or {}
        plan = d.get("action_plan", [])
        if plan:
            next_30_day_goal = plan[0]

    # ── Biggest opportunity ───────────────────────────────────────────
    biggest_opportunity = ""
    if all_recs:
        d = all_recs[0].details or {}
        biggest_opportunity = d.get("expected_outcome", "")
    if not biggest_opportunity and top_pattern:
        biggest_opportunity = f"Grow your channel by doubling down on your strongest content pattern"

    summary = ExecutiveSummary(
        thesis=thesis,
        biggest_opportunity=biggest_opportunity,
        biggest_risk=biggest_risk,
        what_surprised_us=what_surprised_us,
        next_30_day_goal=next_30_day_goal,
        channel_story=channel_story,
        recommendation_ids=[str(r.id) for r in all_recs],
    )

    return summary


def _build_thesis(
    pattern: Pattern | None,
    total_videos: int,
    months_span: int,
) -> str:
    if not pattern:
        return "Your channel data is still being analyzed. Keep publishing to unlock personalized insights."

    metrics = pattern.metrics or {}
    evidence = pattern.evidence or {}

    if pattern.type == "topic_cluster":
        best = metrics.get("best_cluster_name", "one topic")
        worst = metrics.get("worst_cluster_name", "another topic")
        ratio = metrics.get("ratio", 1.0)
        return (
            f"After analyzing {total_videos} videos across {months_span} months, "
            f"one pattern explains most of your channel's performance gap. "
            f"Your {best} content consistently outperforms {worst} content by "
            f"{ratio:.1f}x. The data suggests your fastest path to growth is to "
            f"expand what's already working rather than diversify into new topics."
        )
    elif pattern.type == "series_pattern":
        series_name = metrics.get("series_name", "a content series")
        ratio = metrics.get("ratio", 1.0)
        return (
            f"After analyzing {total_videos} videos across {months_span} months, "
            f"the strongest signal is clear. Your {series_name} series drives "
            f"{ratio:.1f}x more views than standalone content, suggesting that "
            f"serialised, recurring formats are what your audience rewards most."
        )
    elif pattern.type == "title_pattern":
        best_range = metrics.get("best_range", "shorter")
        return (
            f"After analyzing {total_videos} videos across {months_span} months, "
            f"one pattern stands out. Title length directly correlates with "
            f"performance — {best_range} titles consistently attract more views. "
            f"This is the most actionable insight for your next upload."
        )
    return (
        f"After analyzing {total_videos} videos across {months_span} months, "
        f"clear patterns emerged that can guide your content strategy."
    )


def _build_channel_story(
    pattern: Pattern | None,
    total_videos: int,
    months_span: int,
) -> str | None:
    if not pattern:
        return None

    metrics = pattern.metrics or {}
    evidence = pattern.evidence or {}

    if pattern.type == "topic_cluster":
        best = metrics.get("best_cluster_name", "a topic")
        worst = metrics.get("worst_cluster_name", "other topics")
        best_count = 0
        worst_count = 0
        best_cluster = evidence.get("best_cluster", {})
        worst_cluster = evidence.get("worst_cluster", {})
        best_count = best_cluster.get("video_count", 0)
        worst_count = worst_cluster.get("video_count", 0)
        ratio = metrics.get("ratio", 1.0)
        return (
            f"This channel has already proven demand for {best} content, with "
            f"{best_count} videos averaging well above the rest. However, "
            f"{worst_count} uploads focused on {worst} content have diluted "
            f"the channel's overall performance. The audience responds consistently "
            f"when you reinforce a familiar topic, suggesting that focus — not "
            f"volume — is the primary growth constraint."
        )
    elif pattern.type == "series_pattern":
        series_name = metrics.get("series_name", "a content series")
        series_count = metrics.get("series_count", 0)
        ratio = metrics.get("ratio", 1.0)
        return (
            f"This channel's strongest asset is its {series_name} series "
            f"({series_count} videos), which significantly outperforms standalone "
            f"content. Viewers who discover one episode tend to watch the next, "
            f"building both watch time and algorithmic momentum. The evidence "
            f"points to serialized content as the channel's most reliable growth driver."
        )
    elif pattern.type == "title_pattern":
        best_range = metrics.get("best_range", "shorter")
        best_avg = metrics.get("best_avg_views", 0)
        bins = evidence.get("title_length_bins", {})
        total = sum(b.get("count", 0) for b in bins.values())
        return (
            f"This channel's title strategy has room for improvement. Longer titles "
            f"compete for limited viewer attention, especially on mobile, while "
            f"{best_range} titles average {best_avg:,} views. Across {total} uploads, "
            f"the pattern is consistent — shorter, scannable headlines outperform."
        )
    return None


def _build_biggest_risk(
    pattern: Pattern | None,
    recs: tuple[PipelineRecommendation, ...],
) -> str:
    if recs:
        d = recs[0].details or {}
        risk = d.get("risk_of_doing_nothing", "")
        if risk:
            return risk
    if pattern and pattern.type == "topic_cluster":
        metrics = pattern.metrics or {}
        worst_name = metrics.get("worst_cluster_name", "underperforming topics")
        return f"Without shifting focus, {worst_name} content will continue to hold back your channel's growth."
    return "Without addressing the patterns identified above, your channel growth is likely to remain flat."


def _build_surprise(
    top_pattern: Pattern | None,
    all_patterns: tuple[Pattern, ...],
) -> str | None:
    if len(all_patterns) < 2:
        return None

    top = all_patterns[0]
    second = all_patterns[1]

    gap = top.impact_score - second.impact_score
    if gap < 0.15:
        return None

    type_labels = {
        "topic_cluster": "topic selection",
        "series_pattern": "content series",
        "title_pattern": "title length",
    }
    top_label = type_labels.get(top.type, top.type)
    second_label = type_labels.get(second.type, second.type)

    return (
        f"We expected {second_label} to be a meaningful factor, but "
        f"{top_label} has more than {gap:.1f}x the impact on your "
        f"channel's performance."
    )


async def persist_report(
    report: ExecutiveSummary,
    context: ReportContext,
    db: AsyncSession,
) -> ChannelReport:
    """Persist the executive summary to the channel_reports table.

    Clears any previous report for this creator (each run replaces the last).
    """
    from sqlalchemy import delete

    await db.execute(
        delete(ChannelReport).where(
            ChannelReport.creator_profile_id == context.creator_profile_id
        )
    )

    cr = ChannelReport(
        creator_profile_id=context.creator_profile_id,
        analysis_run_id=context.analysis_run_id,
        version=report.version,
        thesis=report.thesis,
        biggest_opportunity=report.biggest_opportunity,
        biggest_risk=report.biggest_risk,
        what_surprised_us=report.what_surprised_us,
        next_30_day_goal=report.next_30_day_goal,
        channel_story=report.channel_story,
        recommendation_ids=report.recommendation_ids,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(cr)
    await db.flush()
    logger.info("Persisted ChannelReport for creator %s", context.creator_profile_id)
    return cr
