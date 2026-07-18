"""IntelligenceStage — Creator Intelligence Engine pipeline integration.

Runs after the ClaimEngine and before the RecommendationEngine.
Produces PipelinePattern artifacts that enrich recommendations with
video-level performance insights.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.base import Pattern
from app.intelligence.orchestrator import (
    run_intelligence_extractors,
    persist_patterns,
)

logger = logging.getLogger(__name__)


@dataclass
class IntelligenceContext:
    """Context for the Intelligence Stage.

    Carries the creator profile ID and any signals from earlier
    pipeline stages that may influence pattern extraction.
    """

    creator_profile_id: UUID
    feature_vector_id: UUID | None = None
    claims: tuple = field(default_factory=tuple)


async def run_intelligence_stage(
    context: IntelligenceContext,
    db: AsyncSession,
) -> list[Pattern]:
    """Run the Creator Intelligence Engine.

    Extracts patterns from video-level data, persists them, and
    returns the in-memory Pattern list for downstream stages.
    """
    patterns = await run_intelligence_extractors(
        creator_profile_id=context.creator_profile_id,
        db=db,
    )

    if patterns:
        await persist_patterns(patterns, context.creator_profile_id, db)

    return patterns
