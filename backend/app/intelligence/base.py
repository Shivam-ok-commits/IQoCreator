"""Base types for the Creator Intelligence Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Pattern:
    """A structured, evidence-backed observation about creator performance.

    Produced by pattern extractors and consumed by the RecommendationEngine.
    Each pattern carries its own confidence, impact, and supporting evidence
    so downstream consumers can rank and filter without re-querying the DB.
    """

    type: str
    summary: str
    explanation: str | None = None
    confidence: float = 0.0
    impact: float = 0.0
    metrics: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    suggested_actions: list[str] = field(default_factory=list)

    @property
    def impact_score(self) -> float:
        return self.confidence * self.impact


class BaseExtractor:
    """Base class for pattern extractors.

    Subclasses implement ``extract()`` which returns zero or more
    ``Pattern`` objects.  The orchestrator collects and persists all
    patterns after every analysis run.
    """

    async def extract(
        self,
        creator_profile_id: UUID,
        db: AsyncSession,  # noqa: F821
    ) -> list[Pattern]:
        raise NotImplementedError
