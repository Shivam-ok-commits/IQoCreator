"""Tests for EvidenceEngine.

Covers: successful evidence generation, confidence calculation,
replay/idempotency, historical persistence, empty findings list,
repository queries.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models import Finding, MetricFeatureVector, PipelineEvidence
from app.pipeline.evidence_engine import EvidenceContext, EvidenceEngine

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_finding(
    finding_id: UUID | None = None,
    rule_id: str = "low_upload_frequency",
    severity: str = "MEDIUM",
    category: str = "publishing",
    title: str = "Low upload frequency",
    evidence: dict | None = None,
) -> Finding:
    f = MagicMock(spec=Finding)
    f.id = finding_id or uuid4()
    f.creator_profile_id = uuid4()
    f.source_feature_vector_id = uuid4()
    f.rule_id = rule_id
    f.severity = severity
    f.category = category
    f.title = title
    f.description = "Test description"
    f.evidence = evidence or {
        "upload_frequency": 0.005,
        "threshold": 0.02,
    }
    return f


def _make_feature_vector(
    features: dict | None = None,
) -> MetricFeatureVector:
    v = MagicMock(spec=MetricFeatureVector)
    v.id = uuid4()
    v.creator_profile_id = uuid4()
    v.features = features or {
        "upload_frequency": 0.005,
        "total_videos": 5,
        "channel_age_days": 250,
        "engagement_rate": 0.04,
        "average_views": 5000,
        "shorts_ratio": 0.1,
    }
    return v


# ── Tests ────────────────────────────────────────────────────────────────


class TestEvidenceEngine:
    """Tests for EvidenceEngine."""

    async def test_successful_evidence_generation(self) -> None:
        """A list of findings produces matching PipelineEvidence artifacts."""
        finding = _make_finding()
        vector = _make_feature_vector()

        finding_repo = AsyncMock()
        evidence_repo = AsyncMock()
        evidence_repo.create_many = AsyncMock(
            side_effect=lambda x: x
        )

        engine = EvidenceEngine(
            finding_repo=finding_repo,
            evidence_repo=evidence_repo,
        )
        context = EvidenceContext(
            findings=(finding,),
            feature_vector=vector,
        )

        results = await engine.execute(context)

        assert len(results) == 1
        ev = results[0]
        assert ev.source_finding_id == finding.id
        assert ev.source_rule_id == finding.rule_id
        assert ev.source_feature_vector_id == finding.source_feature_vector_id
        assert 0.0 <= ev.confidence <= 1.0
        assert ev.supporting_data is not None
        assert ev.explanation is not None

        evidence_repo.create_many.assert_awaited_once()

    async def test_empty_findings_list(self) -> None:
        """No findings produces no evidence artifacts."""
        vector = _make_feature_vector()

        finding_repo = AsyncMock()
        evidence_repo = AsyncMock()
        evidence_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = EvidenceEngine(
            finding_repo=finding_repo,
            evidence_repo=evidence_repo,
        )
        context = EvidenceContext(
            findings=(),
            feature_vector=vector,
        )

        results = await engine.execute(context)
        assert len(results) == 0
        evidence_repo.create_many.assert_not_awaited()

    async def test_multiple_findings_produce_multiple_evidence(self) -> None:
        """Multiple findings produce one evidence each."""
        f1 = _make_finding(rule_id="low_upload_frequency", severity="MEDIUM")
        f2 = _make_finding(rule_id="low_engagement_rate", severity="HIGH")
        f3 = _make_finding(rule_id="new_channel", severity="INFO")
        vector = _make_feature_vector()

        finding_repo = AsyncMock()
        evidence_repo = AsyncMock()
        evidence_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = EvidenceEngine(
            finding_repo=finding_repo,
            evidence_repo=evidence_repo,
        )
        context = EvidenceContext(
            findings=(f1, f2, f3),
            feature_vector=vector,
        )

        results = await engine.execute(context)
        assert len(results) == 3
        rule_ids = {e.source_rule_id for e in results}
        assert rule_ids == {"low_upload_frequency", "low_engagement_rate", "new_channel"}
        evidence_repo.create_many.assert_awaited_once()

    async def test_replay_produces_identical_evidence(self) -> None:
        """Running twice with same inputs produces identical confidence scores."""
        finding = _make_finding()
        vector = _make_feature_vector()

        finding_repo = AsyncMock()
        evidence_repo = AsyncMock()
        evidence_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = EvidenceEngine(
            finding_repo=finding_repo,
            evidence_repo=evidence_repo,
        )
        context = EvidenceContext(
            findings=(finding,),
            feature_vector=vector,
        )

        results1 = await engine.execute(context)
        results2 = await engine.execute(context)

        assert len(results1) == len(results2)
        assert results1[0].confidence == results2[0].confidence
        assert results1[0].explanation == results2[0].explanation

    async def test_confidence_high_for_high_severity(self) -> None:
        """HIGH severity findings get higher confidence scores."""
        vector = _make_feature_vector()

        high_finding = _make_finding(severity="HIGH", rule_id="low_engagement_rate", evidence={
            "engagement_rate": 0.003,
            "threshold": 0.01,
        })
        info_finding = _make_finding(severity="INFO", rule_id="new_channel", evidence={
            "channel_age_days": 30,
            "threshold": 90,
        })

        finding_repo = AsyncMock()
        evidence_repo = AsyncMock()
        evidence_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = EvidenceEngine(
            finding_repo=finding_repo,
            evidence_repo=evidence_repo,
        )
        context = EvidenceContext(
            findings=(high_finding, info_finding),
            feature_vector=vector,
        )

        results = await engine.execute(context)
        high_ev = next(r for r in results if r.source_rule_id == "low_engagement_rate")
        info_ev = next(r for r in results if r.source_rule_id == "new_channel")

        # HIGH severity should have higher confidence than INFO
        assert high_ev.confidence > info_ev.confidence

    async def test_confidence_in_range(self) -> None:
        """All confidence scores are within 0.0–1.0."""
        vector = _make_feature_vector()
        findings = [
            _make_finding(rule_id="low_upload_frequency", severity="MEDIUM"),
            _make_finding(rule_id="low_engagement_rate", severity="HIGH"),
            _make_finding(rule_id="high_shorts_ratio", severity="INFO"),
        ]

        finding_repo = AsyncMock()
        evidence_repo = AsyncMock()
        evidence_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = EvidenceEngine(
            finding_repo=finding_repo,
            evidence_repo=evidence_repo,
        )
        context = EvidenceContext(
            findings=tuple(findings),
            feature_vector=vector,
        )

        results = await engine.execute(context)
        for ev in results:
            assert 0.0 <= ev.confidence <= 1.0

    async def test_supporting_data_contains_rule_info(self) -> None:
        """Supporting data includes rule_id, severity, category, and feature values."""
        finding = _make_finding(rule_id="low_upload_frequency", severity="MEDIUM")
        vector = _make_feature_vector()

        finding_repo = AsyncMock()
        evidence_repo = AsyncMock()
        evidence_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = EvidenceEngine(
            finding_repo=finding_repo,
            evidence_repo=evidence_repo,
        )
        context = EvidenceContext(
            findings=(finding,),
            feature_vector=vector,
        )

        results = await engine.execute(context)
        data = results[0].supporting_data

        assert "rule_id" in data
        assert data["rule_id"] == "low_upload_frequency"
        assert "severity" in data
        assert data["severity"] == "MEDIUM"
        assert "feature_values" in data
        assert isinstance(data["feature_values"], dict)

    async def test_explanation_includes_evidence_values(self) -> None:
        """Explanation contains specific evidence values from the finding."""
        finding = _make_finding(
            rule_id="low_upload_frequency",
            evidence={"upload_frequency": 0.005, "threshold": 0.02},
        )
        vector = _make_feature_vector()

        finding_repo = AsyncMock()
        evidence_repo = AsyncMock()
        evidence_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = EvidenceEngine(
            finding_repo=finding_repo,
            evidence_repo=evidence_repo,
        )
        context = EvidenceContext(
            findings=(finding,),
            feature_vector=vector,
        )

        results = await engine.execute(context)
        explanation = results[0].explanation

        assert explanation is not None
        assert "0.005" in explanation
        assert "0.020" in explanation or "0.02" in explanation
        assert "threshold" in explanation.lower() or "threshold" in explanation


# ── Repository tests ─────────────────────────────────────────────────────


class TestPipelineEvidenceRepository:
    """Tests for PipelineEvidenceRepository persistence."""

    async def test_create_and_retrieve_by_id(self) -> None:
        """A created evidence artifact can be retrieved by ID."""
        db_session = AsyncMock()
        from app.repositories.pipeline_evidence_repo import (
            PipelineEvidenceRepository,
        )
        repo = PipelineEvidenceRepository(db_session)
        evidence_id = uuid4()

        ev = MagicMock(spec=PipelineEvidence)
        ev.id = evidence_id

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=ev)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(evidence_id)
        assert result is not None
        assert result.id == evidence_id

    async def test_get_by_finding_returns_evidence(self) -> None:
        """get_by_finding returns the evidence for a given finding."""
        db_session = AsyncMock()
        from app.repositories.pipeline_evidence_repo import (
            PipelineEvidenceRepository,
        )
        repo = PipelineEvidenceRepository(db_session)
        finding_id = uuid4()

        mock_result = AsyncMock()
        expected = MagicMock(spec=PipelineEvidence)
        expected.source_finding_id = finding_id
        mock_result.scalar_one_or_none = AsyncMock(return_value=expected)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_finding(finding_id)
        assert result is not None
        assert result.source_finding_id == finding_id

    async def test_get_by_creator_returns_all_evidence(self) -> None:
        """get_by_creator returns all evidence for a creator."""
        db_session = AsyncMock()
        from app.repositories.pipeline_evidence_repo import (
            PipelineEvidenceRepository,
        )
        repo = PipelineEvidenceRepository(db_session)
        creator_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars = AsyncMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        db_session.execute = AsyncMock(return_value=mock_result)

        results = await repo.get_by_creator(creator_id)
        assert isinstance(results, list)
