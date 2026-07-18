"""ClaimEngine — transform PipelineEvidence into immutable Claim artifacts.

Consumes PipelineEvidence artifacts, transforms evidence data into
concise, deterministic claims. No AI, no recommendations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.models import PipelineClaim, PipelineEvidence
from app.repositories.claim_repo import ClaimRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClaimContext:
    """Immutable context for claim generation.

    Carries the evidence artifacts to transform into claims.
    """

    evidence_list: tuple[PipelineEvidence, ...]


class ClaimEngine:
    """Generates PipelineClaim artifacts from PipelineEvidence.

    Responsibilities
    -----------------
    1. For each evidence artifact, generate a deterministic claim.
    2. Produce a concise summary and rationale for each claim.
    3. Persist the resulting PipelineClaim artifacts.

    Non-responsibilities
    ---------------------
    - Does not access the database directly (receives evidence objects).
    - Does not use AI/LLM.
    - Does not generate recommendations.
    - Does not mutate evidence artifacts.
    """

    def __init__(
        self,
        *,
        claim_repo: ClaimRepository,
    ) -> None:
        self._claim_repo = claim_repo

    async def execute(
        self,
        context: ClaimContext,
    ) -> list[PipelineClaim]:
        """Generate a claim for each evidence artifact.

        Parameters
        ----------
        context : ClaimContext
            Contains the evidence artifacts to process.

        Returns
        -------
        list[PipelineClaim]
            One PipelineClaim per evidence artifact, persisted.
        """
        claims: list[PipelineClaim] = []

        for evidence in context.evidence_list:
            claim = self._build_claim(evidence)
            claims.append(claim)

        if claims:
            await self._claim_repo.create_many(claims)
            logger.info(
                "ClaimEngine created %d claim artifacts",
                len(claims),
            )

        return claims

    def _build_claim(
        self,
        evidence: PipelineEvidence,
    ) -> PipelineClaim:
        """Build a single PipelineClaim from PipelineEvidence.

        Pure function — no side effects, no database access.
        """
        rule_id = evidence.source_rule_id
        supporting_data = evidence.supporting_data or {}

        category = (
            supporting_data.get("category")
            or supporting_data.get("rule_id")
            or "general"
        )
        severity = supporting_data.get("severity", "INFO")
        confidence = evidence.confidence

        summary = self._generate_summary(rule_id, supporting_data, confidence)
        rationale = self._generate_rationale(evidence, supporting_data)

        return PipelineClaim(
            id=uuid4(),
            creator_profile_id=evidence.creator_profile_id,
            source_evidence_id=evidence.id,
            category=str(category),
            severity=str(severity),
            confidence=confidence,
            summary=summary,
            rationale=rationale,
            supporting_evidence_ids=[str(evidence.id)],
        )

    @staticmethod
    def _generate_summary(
        rule_id: str,
        supporting_data: dict,
        confidence: float,
    ) -> str:
        """Generate a concise, deterministic summary from evidence data.

        Templates per rule_id — pure functions of the evidence.
        """
        summaries = {
            "low_upload_frequency": (
                "The channel publishes significantly less frequently "
                "than the expected baseline."
            ),
            "low_engagement_rate": (
                "Audience engagement is notably lower than typical "
                "channel performance metrics."
            ),
            "high_shorts_ratio": (
                "A substantial portion of uploads are short-form content, "
                "which may limit long-form audience development."
            ),
            "low_average_views": (
                "Average views per video are below the recommended "
                "threshold, indicating potential reach challenges."
            ),
            "inconsistent_publishing": (
                "Upload patterns show large gaps between publications, "
                "suggesting an inconsistent content schedule."
            ),
            "new_channel": (
                "The channel is in its early growth phase, presenting "
                "opportunities to establish audience discovery patterns."
            ),
        }

        template = summaries.get(rule_id)
        if template:
            return template

        title = supporting_data.get("finding_title", "Channel observation")
        return f"{title} — review recommended."

    @staticmethod
    def _generate_rationale(
        evidence: PipelineEvidence,
        supporting_data: dict,
    ) -> str:
        """Generate a deterministic rationale from the evidence data."""
        rule_id = evidence.source_rule_id
        explanation = evidence.explanation or ""
        confidence = evidence.confidence

        rule_labels = {
            "low_upload_frequency": "Upload frequency analysis",
            "low_engagement_rate": "Engagement rate analysis",
            "high_shorts_ratio": "Content format analysis",
            "low_average_views": "Viewership analysis",
            "inconsistent_publishing": "Publishing pattern analysis",
            "new_channel": "Channel age analysis",
        }
        label = rule_labels.get(rule_id, "Channel analysis")

        return (
            f"{label}: {explanation} "
            f"(confidence: {confidence:.2f})"
        )
