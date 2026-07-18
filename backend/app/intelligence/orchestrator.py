"""IntelligenceOrchestrator — runs all pattern extractors and persists results."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.base import Pattern
from app.intelligence.extractors.topic_clusters import TopicClusterExtractor
from app.intelligence.extractors.series_pattern import SeriesPatternExtractor
from app.intelligence.extractors.title_patterns import TitlePatternExtractor
from app.models import PipelinePattern

logger = logging.getLogger(__name__)


async def run_intelligence_extractors(
    creator_profile_id: UUID,
    db: AsyncSession,
) -> list[Pattern]:
    """Run all registered pattern extractors and return collected patterns.

    Each extractor runs independently (no ordering dependency).  Patterns
    are sorted by impact_score descending so the highest-value insights
    come first.
    """
    extractors = [
        TopicClusterExtractor(),
        SeriesPatternExtractor(),
        TitlePatternExtractor(),
    ]

    all_patterns: list[Pattern] = []
    for extractor in extractors:
        try:
            patterns = await extractor.extract(creator_profile_id, db)
            all_patterns.extend(patterns)
            logger.info(
                "%s produced %d pattern(s)",
                extractor.__class__.__name__,
                len(patterns),
            )
        except Exception:
            logger.exception(
                "Extractor %s failed for creator %s",
                extractor.__class__.__name__,
                creator_profile_id,
            )

    all_patterns.sort(key=lambda p: p.impact_score, reverse=True)
    logger.info("Intelligence stage complete: %d pattern(s)", len(all_patterns))
    return all_patterns


async def persist_patterns(
    patterns: list[Pattern],
    creator_profile_id: UUID,
    db: AsyncSession,
) -> None:
    """Persist computed patterns to the pipeline_patterns table.

    Clears previous patterns for this creator first (append-only would
    accumulate stale observations).
    """
    from sqlalchemy import delete

    await db.execute(
        delete(PipelinePattern).where(
            PipelinePattern.creator_profile_id == creator_profile_id
        )
    )

    for p in patterns:
        db.add(PipelinePattern(
            creator_profile_id=creator_profile_id,
            pattern_type=p.type,
            summary=p.summary,
            explanation=p.explanation,
            confidence=p.confidence,
            impact=p.impact,
            impact_score=p.impact_score,
            metrics=p.metrics,
            evidence=p.evidence,
            suggested_actions=p.suggested_actions,
        ))

    await db.flush()
    logger.info("Persisted %d pattern(s) for creator %s", len(patterns), creator_profile_id)
