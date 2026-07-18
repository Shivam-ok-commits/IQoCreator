"""EvidenceEngine — enrich Findings with structured supporting evidence.

Consumes Finding artifacts, computes deterministic confidence scores,
and produces PipelineEvidence artifacts. No AI, no recommendations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.models import Finding, MetricFeatureVector, PipelineEvidence
from app.repositories.finding_repo import FindingRepository
from app.repositories.pipeline_evidence_repo import PipelineEvidenceRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvidenceContext:
    """Immutable context for evidence generation.

    Carries the artifacts needed to produce evidence for each finding.
    """

    findings: tuple[Finding, ...]
    feature_vector: MetricFeatureVector


class EvidenceEngine:
    """Generates PipelineEvidence artifacts from Findings.

    Responsibilities
    -----------------
    1. For each Finding, compute a deterministic confidence score.
    2. Build structured supporting_data from the finding's evidence.
    3. Generate a deterministic explanation template.
    4. Persist the resulting PipelineEvidence artifacts.

    Non-responsibilities
    ---------------------
    - Does not access the database directly (receives Finding objects).
    - Does not use AI/LLM.
    - Does not generate claims or recommendations.
    - Does not mutate Finding artifacts.
    """

    def __init__(
        self,
        *,
        finding_repo: FindingRepository,
        evidence_repo: PipelineEvidenceRepository,
    ) -> None:
        self._finding_repo = finding_repo
        self._evidence_repo = evidence_repo

    async def execute(
        self,
        context: EvidenceContext,
    ) -> list[PipelineEvidence]:
        """Generate evidence for each finding.

        Parameters
        ----------
        context : EvidenceContext
            Contains the findings and feature vector to process.

        Returns
        -------
        list[PipelineEvidence]
            One PipelineEvidence per finding, persisted.
        """
        evidence_list: list[PipelineEvidence] = []

        for finding in context.findings:
            ev = self._build_evidence(finding, context.feature_vector)
            evidence_list.append(ev)

        if evidence_list:
            await self._evidence_repo.create_many(evidence_list)
            logger.info(
                "EvidenceEngine created %d evidence artifacts",
                len(evidence_list),
            )

        return evidence_list

    def _build_evidence(
        self,
        finding: Finding,
        feature_vector: MetricFeatureVector,
    ) -> PipelineEvidence:
        """Build a single PipelineEvidence from a Finding.

        This is a pure function — no side effects, no database access.
        """
        # ── 1. Compute confidence ──────────────────────────────────
        confidence = self._compute_confidence(finding, feature_vector)

        # ── 2. Build supporting data ───────────────────────────────
        supporting_data: dict[str, object] = {}
        if finding.evidence:
            supporting_data.update(finding.evidence)

        supporting_data["rule_id"] = finding.rule_id
        supporting_data["severity"] = finding.severity
        supporting_data["category"] = finding.category
        supporting_data["finding_title"] = finding.title
        supporting_data["feature_values"] = self._get_relevant_features(
            finding.rule_id, feature_vector
        )

        # ── 3. Generate explanation ────────────────────────────────
        explanation = self._generate_explanation(finding, confidence)

        return PipelineEvidence(
            id=uuid4(),
            creator_profile_id=finding.creator_profile_id,
            source_finding_id=finding.id,
            source_feature_vector_id=finding.source_feature_vector_id,
            source_rule_id=finding.rule_id,
            confidence=confidence,
            supporting_data=supporting_data,
            explanation=explanation,
        )

    @staticmethod
    def _get_rule_feature_keys(rule_id: str) -> list[str]:
        """Return the feature keys relevant to a given rule."""
        rule_feature_map = {
            "low_upload_frequency": ["upload_frequency", "total_videos", "channel_age_days"],
            "low_engagement_rate": ["engagement_rate", "average_views", "average_likes", "average_comments"],
            "high_shorts_ratio": ["shorts_ratio", "total_videos", "average_duration"],
            "low_average_views": ["average_views", "total_videos"],
            "inconsistent_publishing": ["upload_frequency", "total_videos", "channel_age_days"],
            "new_channel": ["channel_age_days", "total_videos"],
        }
        keys = rule_feature_map.get(rule_id)
        if keys is None:
            logger.warning("No feature mapping for rule '%s'", rule_id)
            return []
        return keys

    @staticmethod
    def _compute_confidence(
        finding: Finding,
        feature_vector: MetricFeatureVector,
    ) -> float:
        """Compute a deterministic confidence score (0.0–1.0).

        Factors:
        - Severity weight: HIGH=0.9, MEDIUM=0.7, LOW=0.5, INFO=0.4
        - Distance from threshold: how far the value is from the rule threshold
        - Data completeness: whether the per-rule required features are non-null
        """
        # Severity baseline
        severity_map = {
            "HIGH": 0.9,
            "MEDIUM": 0.7,
            "LOW": 0.5,
            "INFO": 0.4,
        }
        base = severity_map.get(finding.severity, 0.5)

        # Distance from threshold — estimate from evidence if available
        distance_factor = 1.0
        if finding.evidence:
            threshold = finding.evidence.get("threshold")
            feature_keys = [
                k for k in finding.evidence
                if k not in ("threshold", "rule_id", "severity", "category", "finding_title")
            ]
            if threshold is not None and feature_keys:
                values = [
                    finding.evidence[k]
                    for k in feature_keys
                    if isinstance(finding.evidence.get(k), (int, float))
                ]
                if values and isinstance(threshold, (int, float)):
                    max_distance = max(
                        abs(v - threshold) for v in values
                    )
                    distance_factor = min(
                        1.0, max_distance / max(threshold * 2, 0.01)
                    )

        # Per-rule data completeness (only features relevant to this rule)
        relevant_keys = EvidenceEngine._get_rule_feature_keys(finding.rule_id)
        if relevant_keys:
            complete = sum(
                1 for k in relevant_keys
                if feature_vector.features.get(k) is not None
            )
            completeness = complete / len(relevant_keys)
        else:
            completeness = 0.5  # Neutral if no feature mapping

        # Final score: weighted combination
        score = base * 0.5 + distance_factor * 0.3 + completeness * 0.2
        return round(min(max(score, 0.0), 1.0), 4)

    @staticmethod
    def _get_relevant_features(
        rule_id: str,
        feature_vector: MetricFeatureVector,
    ) -> dict[str, object]:
        """Extract features relevant to a specific rule."""
        relevant: dict[str, object] = {}
        keys = EvidenceEngine._get_rule_feature_keys(rule_id)
        for k in keys:
            val = feature_vector.features.get(k)
            if val is not None:
                relevant[k] = val
        return relevant

    @staticmethod
    def _generate_explanation(
        finding: Finding,
        confidence: float,
    ) -> str:
        """Generate a deterministic explanation with evidence values."""
        confidence_label = (
            "High confidence" if confidence >= 0.8
            else "Moderate confidence" if confidence >= 0.5
            else "Low confidence"
        )

        # Include specific evidence values in the explanation
        value_str = ""
        if finding.evidence:
            parts = []
            for k, v in finding.evidence.items():
                if k in ("threshold", "rule_id", "severity", "category", "finding_title"):
                    continue
                if isinstance(v, (int, float)):
                    parts.append(f"{k}={v:.3f}")
            if parts:
                value_str = f" ({'; '.join(parts)})"

        threshold_str = ""
        if finding.evidence and "threshold" in finding.evidence:
            t = finding.evidence["threshold"]
            if isinstance(t, (int, float)):
                threshold_str = f" (threshold: {t})"

        return (
            f"{confidence_label}: {finding.title}. "
            f"Current values{value_str} are outside the recommended range{threshold_str}. "
            f"This {finding.severity}-severity finding is based on {finding.category} metrics."
        )
