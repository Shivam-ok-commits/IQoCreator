"""RecommendationEngine — transforms Pattern objects into consultant-style recommendations.

Terminal pipeline stage. Consumes intelligence patterns and pipeline claims,
produces deterministic recommendations enriched with creator-specific evidence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.intelligence.base import Pattern
from app.models import PipelineClaim, PipelineRecommendation
from app.pipeline.renderers.base import build_recommendation_data, compute_strength
from app.pipeline.renderers.topic_renderer import TopicRenderer
from app.pipeline.renderers.series_renderer import SeriesRenderer
from app.pipeline.renderers.title_renderer import TitleRenderer
from app.repositories.recommendation_repo import RecommendationRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecommendationContext:
    """Immutable context for recommendation generation.

    Carries both claim artifacts and intelligence patterns so the
    engine can produce evidence-backed, creator-specific recommendations.
    """

    claims: tuple[PipelineClaim, ...]
    patterns: tuple[Pattern, ...] = field(default_factory=tuple)


_RENDERERS = {
    "topic_cluster": TopicRenderer(),
    "series_pattern": SeriesRenderer(),
    "title_pattern": TitleRenderer(),
}


class RecommendationEngine:
    """Generates PipelineRecommendation artifacts from Patterns + Claims.

    Responsibilities
    -----------------
    1. Route each high-impact pattern to its type-specific renderer.
    2. Build a deterministic, consultant-style recommendation.
    3. Persist the resulting PipelineRecommendation artifacts.

    Non-responsibilities
    ---------------------
    - Does not access the database directly (receives pre-loaded objects).
    - Does not use AI/LLM.
    """

    def __init__(
        self,
        *,
        recommendation_repo: RecommendationRepository,
    ) -> None:
        self._rec_repo = recommendation_repo

    async def execute(
        self,
        context: RecommendationContext,
    ) -> list[PipelineRecommendation]:
        """Generate recommendations from intelligence patterns and claims.

        Pattern-based recommendations use type-specific renderers.
        Claim-based recommendations use a fallback structure.

        Parameters
        ----------
        context : RecommendationContext
            Contains patterns and claim artifacts.

        Returns
        -------
        list[PipelineRecommendation]
            All generated recommendations, persisted.
        """
        recs: list[PipelineRecommendation] = []

        creator_profile_id = (
            context.claims[0].creator_profile_id
            if context.claims else UUID(int=0)
        )

        # ── Pattern-based recommendations ────────────────────────────
        for pattern in context.patterns:
            if pattern.impact_score < 0.2:
                continue

            rec = self._build_pattern_recommendation(pattern, creator_profile_id)
            if rec:
                recs.append(rec)

        # ── Claim-based recommendations (fallback) ───────────────────
        for claim in context.claims:
            rec = self._build_claim_recommendation(claim)
            if rec:
                recs.append(rec)

        if recs:
            await self._rec_repo.create_many(recs)
            logger.info(
                "RecommendationEngine created %d artifacts "
                "(%d from patterns, %d from claims)",
                len(recs),
                sum(1 for p in context.patterns if p.impact_score >= 0.2),
                len(context.claims),
            )

        return recs

    def _build_pattern_recommendation(
        self,
        pattern: Pattern,
        creator_profile_id: UUID,
    ) -> PipelineRecommendation | None:
        renderer = _RENDERERS.get(pattern.type)
        if not renderer:
            return None

        try:
            details = renderer.render(pattern)
        except Exception:
            logger.exception("Renderer failed for pattern type %s", pattern.type)
            return None

        if not details:
            return None

        priority = "HIGH" if pattern.impact_score >= 0.5 else "MEDIUM"
        headline = details.get("headline", pattern.summary)
        expected = details.get("expected_outcome", f"+{round(pattern.impact * 100)}%")

        return PipelineRecommendation(
            id=uuid4(),
            creator_profile_id=creator_profile_id,
            source_claim_id=None,
            priority=priority,
            category=f"pattern_{pattern.type}",
            title=headline,
            description=details.get("observation", pattern.summary),
            expected_outcome=expected,
            success_metric=f"Strength: {pattern.confidence:.0%}",
            details=details,
        )

    def _build_claim_recommendation(
        self,
        claim: PipelineClaim,
    ) -> PipelineRecommendation | None:
        """Build a fallback recommendation from a PipelineClaim."""

        category_labels = {
            "publishing": {
                "headline": "Increase your upload frequency",
                "observation": "Your publishing schedule is inconsistent.",
                "why": "Regular uploads improve audience retention and algorithmic discovery.",
                "action": "Publish at least one video per week for the next 30 days.",
                "outcome": "+20–40% subscriber growth within 90 days",
            },
            "engagement": {
                "headline": "Improve audience retention in your first 30 seconds",
                "observation": "Your engagement metrics suggest viewers drop off early.",
                "why": "The first 30 seconds determine whether a viewer stays or leaves.",
                "action": "Hook viewers in the first 5 seconds with a clear promise of what they'll learn.",
                "outcome": "+15–30% engagement rate",
            },
            "content_format": {
                "headline": "Balance short-form with long-form content",
                "observation": "Your channel is heavily weighted toward one format.",
                "why": "Long-form content builds deeper audience connection and watch time.",
                "action": "Aim for at least 50% long-form uploads over the next month.",
                "outcome": "+25% watch time growth",
            },
            "performance": {
                "headline": "Optimize titles for search discovery",
                "observation": "Your titles may not be matching what viewers search for.",
                "why": "YouTube's algorithm ranks videos based on title relevance to search queries.",
                "action": "Research keywords in your niche and include the primary keyword in your title.",
                "outcome": "+20–40% average views",
            },
            "growth": {
                "headline": "Keep publishing — your data is building",
                "observation": "Your channel is still gathering performance data.",
                "why": "More data means more precise recommendations in future analyses.",
                "action": "Continue uploading consistently and experiment with different formats.",
                "outcome": "Clear optimization path within 90 days",
            },
        }

        label = category_labels.get(claim.category, {
            "headline": "Review your content strategy",
            "observation": "There may be optimization opportunities in your recent uploads.",
            "why": "Small changes to format or topic can significantly impact performance.",
            "action": "Review your best and worst performing videos to identify patterns.",
            "outcome": "+10–25% overall channel growth",
        })

        details = build_recommendation_data(
            pattern_type=f"claim_{claim.category}",
            headline=label["headline"],
            observation=label["observation"],
            evidence=[claim.rationale] if claim.rationale else [],
            why_it_matters=label["why"],
            action_plan=[label["action"]],
            expected_outcome=label["outcome"],
            risk_of_doing_nothing=(
                "Without addressing this issue, your channel growth will "
                "likely remain flat or decline gradually."
            ),
            strength=compute_strength(
                level="Medium",
                rating=3,
                because=[
                    "Based on channel-level metrics",
                    "General pattern observed across similar channels",
                ],
            ),
            impact=0.5,
            why_now="This recommendation is based on established channel benchmarks.",
        )

        priority = label.get("priority", "MEDIUM")

        return PipelineRecommendation(
            id=uuid4(),
            creator_profile_id=claim.creator_profile_id,
            source_claim_id=claim.id,
            priority=priority,
            category=claim.category,
            title=label["headline"],
            description=label["observation"],
            expected_outcome=label["outcome"],
            success_metric="Positive trend in key metrics",
            details=details,
        )
