"""Tests for ClaimEngine.

Covers: successful claim generation, replay/idempotency, historical
persistence, empty evidence list, repository queries, content verified.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models import PipelineClaim, PipelineEvidence
from app.pipeline.claim_engine import ClaimContext, ClaimEngine

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_evidence(
    evidence_id: UUID | None = None,
    rule_id: str = "low_upload_frequency",
    confidence: float = 0.87,
    severity: str = "MEDIUM",
    category: str = "publishing",
) -> PipelineEvidence:
    ev = MagicMock(spec=PipelineEvidence)
    ev.id = evidence_id or uuid4()
    ev.creator_profile_id = uuid4()
    ev.source_finding_id = uuid4()
    ev.source_feature_vector_id = uuid4()
    ev.source_rule_id = rule_id
    ev.confidence = confidence
    ev.supporting_data = {
        "upload_frequency": 0.005,
        "threshold": 0.02,
        "severity": severity,
        "category": category,
        "finding_title": "Low upload frequency",
        "rule_id": rule_id,
        "feature_values": {"upload_frequency": 0.005},
    }
    ev.explanation = (
        "High confidence: Low upload frequency. "
        "Current values (upload_frequency=0.005) are outside "
        "the recommended range (threshold: 0.02)."
    )
    return ev


# ── Tests ────────────────────────────────────────────────────────────────


class TestClaimEngine:
    """Tests for ClaimEngine."""

    async def test_successful_claim_generation(self) -> None:
        """Evidence produces a PipelineClaim with all required fields."""
        evidence = _make_evidence()
        claim_repo = AsyncMock()
        claim_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = ClaimEngine(claim_repo=claim_repo)
        context = ClaimContext(evidence_list=(evidence,))

        results = await engine.execute(context)

        assert len(results) == 1
        claim = results[0]
        assert claim.source_evidence_id == evidence.id
        assert claim.confidence == evidence.confidence
        assert claim.severity == "MEDIUM"
        assert claim.category == "publishing"
        assert claim.summary is not None
        assert claim.rationale is not None
        assert len(claim.supporting_evidence_ids) == 1
        assert str(evidence.id) in claim.supporting_evidence_ids

        claim_repo.create_many.assert_awaited_once()

    async def test_empty_evidence_list(self) -> None:
        """No evidence produces no claim artifacts."""
        claim_repo = AsyncMock()
        claim_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = ClaimEngine(claim_repo=claim_repo)
        context = ClaimContext(evidence_list=())

        results = await engine.execute(context)
        assert len(results) == 0
        claim_repo.create_many.assert_not_awaited()

    async def test_multiple_evidence_produces_multiple_claims(self) -> None:
        """Multiple evidence artifacts produce one claim each."""
        e1 = _make_evidence(rule_id="low_upload_frequency")
        e2 = _make_evidence(rule_id="low_engagement_rate")
        e3 = _make_evidence(rule_id="new_channel")

        claim_repo = AsyncMock()
        claim_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = ClaimEngine(claim_repo=claim_repo)
        context = ClaimContext(evidence_list=(e1, e2, e3))

        results = await engine.execute(context)
        assert len(results) == 3
        claim_repo.create_many.assert_awaited_once()

    async def test_replay_produces_identical_claims(self) -> None:
        """Same evidence produces identical summaries and rationales."""
        evidence = _make_evidence()

        claim_repo = AsyncMock()
        claim_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = ClaimEngine(claim_repo=claim_repo)
        context = ClaimContext(evidence_list=(evidence,))

        results1 = await engine.execute(context)
        results2 = await engine.execute(context)

        assert len(results1) == len(results2)
        assert results1[0].summary == results2[0].summary
        assert results1[0].rationale == results2[0].rationale
        assert results1[0].confidence == results2[0].confidence

    async def test_claim_content_verified_from_known_evidence(self) -> None:
        """Claim summary matches expected template for each rule."""
        evidence = _make_evidence(rule_id="low_upload_frequency")

        claim_repo = AsyncMock()
        claim_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = ClaimEngine(claim_repo=claim_repo)
        context = ClaimContext(evidence_list=(evidence,))

        results = await engine.execute(context)
        summary = results[0].summary

        assert "publishes" in summary.lower()
        assert "less frequently" in summary.lower()

    async def test_rationale_includes_explanation(self) -> None:
        """Rationale contains the evidence explanation and confidence."""
        evidence = _make_evidence(rule_id="low_upload_frequency", confidence=0.87)

        claim_repo = AsyncMock()
        claim_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = ClaimEngine(claim_repo=claim_repo)
        context = ClaimContext(evidence_list=(evidence,))

        results = await engine.execute(context)
        rationale = results[0].rationale

        assert rationale is not None
        assert "Upload frequency analysis" in rationale
        assert "0.87" in rationale


# ── Repository tests ─────────────────────────────────────────────────────


class TestClaimRepository:
    """Tests for ClaimRepository persistence."""

    async def test_create_and_retrieve_by_id(self) -> None:
        """A created claim can be retrieved by ID."""
        db_session = AsyncMock()
        from app.repositories.claim_repo import ClaimRepository

        repo = ClaimRepository(db_session)
        claim_id = uuid4()

        claim = MagicMock(spec=PipelineClaim)
        claim.id = claim_id

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=claim)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(claim_id)
        assert result is not None
        assert result.id == claim_id

    async def test_get_by_evidence_returns_claim(self) -> None:
        """get_by_evidence returns the claim for a given evidence."""
        db_session = AsyncMock()
        from app.repositories.claim_repo import ClaimRepository

        repo = ClaimRepository(db_session)
        evidence_id = uuid4()

        mock_result = AsyncMock()
        expected = MagicMock(spec=PipelineClaim)
        expected.source_evidence_id = evidence_id
        mock_result.scalar_one_or_none = AsyncMock(return_value=expected)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_evidence(evidence_id)
        assert result is not None
        assert result.source_evidence_id == evidence_id

    async def test_get_by_creator_returns_list(self) -> None:
        """get_by_creator returns all claims for a creator."""
        db_session = AsyncMock()
        from app.repositories.claim_repo import ClaimRepository

        repo = ClaimRepository(db_session)
        creator_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars = AsyncMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        db_session.execute = AsyncMock(return_value=mock_result)

        results = await repo.get_by_creator(creator_id)
        assert isinstance(results, list)
