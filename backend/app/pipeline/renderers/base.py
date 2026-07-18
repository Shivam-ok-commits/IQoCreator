"""Base renderer — every pattern renderer produces a recommendation dict with structured fields."""

from __future__ import annotations

from app.intelligence.base import Pattern


def compute_strength(
    level: str,
    rating: int,
    because: list[str],
) -> dict:
    """Build a recommendation strength object.

    Parameters
    ----------
    level : str
        Qualitative label — "High", "Medium", or "Low".
    rating : int
        1–5 star rating.
    because : list[str]
        Human-readable reasons that explain the rating.
    """
    return {
        "level": level,
        "rating": rating,
        "because": because,
    }


def build_recommendation_data(
    headline: str,
    observation: str,
    evidence: list[str],
    why_it_matters: str,
    action_plan: list[str],
    expected_outcome: str,
    risk_of_doing_nothing: str,
    strength: dict,
    impact: float,
    pattern_type: str,
    supporting_video_ids: list[str] | None = None,
    supporting_videos: list[dict] | None = None,
    why_now: str = "",
) -> dict:
    """Build the structured details dict for a consultant-style recommendation.

    This dict is stored in PipelineRecommendation.details and used
    by the frontend to render the recommendation card.

    Schema version 1 fields:

        version              — always 1 (bump on breaking changes)
        type                 — pattern type (topic_cluster, series_pattern, ...)
        headline             — one-line action-oriented title
        observation          — what the data shows
        evidence             — bullet lines supporting the observation
        why_it_matters       — strategic context
        action_plan          — ordered steps the creator should take
        expected_outcome     — what success looks like
        risk_of_doing_nothing — what happens if the creator ignores this
        strength             — recommendation strength (level, rating, because)
        impact               — 0.0–1.0 estimated impact
        supporting_video_ids — platform video IDs used as evidence
        supporting_videos    — [{title, views, type}] for inline visual proof
        why_now              — explains why this recommendation is top priority
    """
    return {
        "version": 1,
        "type": pattern_type,
        "headline": headline,
        "observation": observation,
        "evidence": evidence,
        "why_it_matters": why_it_matters,
        "action_plan": action_plan,
        "expected_outcome": expected_outcome,
        "risk_of_doing_nothing": risk_of_doing_nothing,
        "strength": strength,
        "impact": round(impact, 2),
        "supporting_video_ids": supporting_video_ids or [],
        "supporting_videos": supporting_videos or [],
        "why_now": why_now,
    }


class BaseRenderer:
    """Override ``render()`` to produce (headline, details) from a pattern."""

    def render(self, pattern: Pattern) -> dict | None:
        raise NotImplementedError
