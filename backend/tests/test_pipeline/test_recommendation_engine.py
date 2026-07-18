"""Tests for RecommendationEngine.

Covers: successful generation, priority assignment, replay/idempotency,
historical persistence, empty claims list, repository queries,
content verified against known claims.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models import PipelineClaim, PipelineRecommendation
from app.pipeline.recommendation_engine import (
    RecommendationContext,
    RecommendationEngine,
)

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_claim(
    claim_id: UUID | None = None,
    category: str = "publishing",
    severity: str = "HIGH",
    summary: str = "The channel publishes less frequently than expected.",
) -> PipelineClaim:
    c = MagicMock(spec=PipelineClaim)
    c.id = claim_id or uuid4()
    c.creator_profile_id = uuid4()
    c.source_evidence_id = uuid4()
    c.category = category
    c.severity = severity
    c.summary = summary
    return c


# ── Tests ────────────────────────────────────────────────────────────────


class TestRecommendationEngine:
    """Tests for RecommendationEngine."""

    async def test_successful_recommendation_generation(self) -> None:
        """A claim produces a recommendation with all required fields."""
        claim = _make_claim(category="publishing")
        rec_repo = AsyncMock()
        rec_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = RecommendationEngine(recommendation_repo=rec_repo)
        context = RecommendationContext(claims=(claim,))

        results = await engine.execute(context)

        assert len(results) == 1
        rec = results[0]
        assert rec.source_claim_id == claim.id
        assert rec.creator_profile_id == claim.creator_profile_id
        assert rec.category == "publishing"
        assert rec.priority in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert rec.title is not None
        assert rec.description is not None
        assert rec.expected_outcome is not None
        assert rec.success_metric is not None

        rec_repo.create_many.assert_awaited_once()

    async def test_priority_assignment(self) -> None:
        """Different claim categories receive different priorities."""
        categories = {
            "publishing": "HIGH",
            "engagement": "CRITICAL",
            "content_format": "MEDIUM",
            "performance": "HIGH",
            "growth": "LOW",
        }

        rec_repo = AsyncMock()
        rec_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = RecommendationEngine(recommendation_repo=rec_repo)

        for cat, expected_priority in categories.items():
            claim = _make_claim(category=cat)
            context = RecommendationContext(claims=(claim,))
            results = await engine.execute(context)

            assert len(results) == 1
            assert results[0].category == cat
            assert results[0].priority == expected_priority, (
                f"Expected {expected_priority} for {cat}, "
                f"got {results[0].priority}"
            )

    async def test_empty_claims_list(self) -> None:
        """No claims produces no recommendations."""
        rec_repo = AsyncMock()
        rec_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = RecommendationEngine(recommendation_repo=rec_repo)
        context = RecommendationContext(claims=())

        results = await engine.execute(context)
        assert len(results) == 0
        rec_repo.create_many.assert_not_awaited()

    async def test_multiple_claims_produce_multiple_recommendations(self) -> None:
        """Multiple claims produce one recommendation each."""
        claims = [
            _make_claim(category="publishing"),
            _make_claim(category="engagement"),
            _make_claim(category="growth"),
        ]

        rec_repo = AsyncMock()
        rec_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = RecommendationEngine(recommendation_repo=rec_repo)
        context = RecommendationContext(claims=tuple(claims))

        results = await engine.execute(context)
        assert len(results) == 3
        rec_repo.create_many.assert_awaited_once()

    async def test_replay_produces_identical_recommendations(self) -> None:
        """Same claim produces identical title, description, and priority."""
        claim = _make_claim(category="publishing")

        rec_repo = AsyncMock()
        rec_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = RecommendationEngine(recommendation_repo=rec_repo)
        context = RecommendationContext(claims=(claim,))

        results1 = await engine.execute(context)
        results2 = await engine.execute(context)

        assert len(results1) == len(results2)
        assert results1[0].title == results2[0].title
        assert results1[0].description == results2[0].description
        assert results1[0].priority == results2[0].priority
        assert results1[0].expected_outcome == results2[0].expected_outcome

    async def test_content_verified_from_known_claim(self) -> None:
        """Publishing claim produces 'Increase upload cadence' recommendation."""
        claim = _make_claim(category="publishing")

        rec_repo = AsyncMock()
        rec_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = RecommendationEngine(recommendation_repo=rec_repo)
        context = RecommendationContext(claims=(claim,))

        results = await engine.execute(context)
        rec = results[0]

        assert "upload" in rec.title.lower()
        assert rec.expected_outcome is not None
        assert "subscriber" in rec.expected_outcome.lower()

    async def test_unknown_category_uses_default(self) -> None:
        """An unmapped category falls back to a default template."""
        claim = _make_claim(category="unknown_category")

        rec_repo = AsyncMock()
        rec_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = RecommendationEngine(recommendation_repo=rec_repo)
        context = RecommendationContext(claims=(claim,))

        results = await engine.execute(context)
        assert len(results) == 1
        assert results[0].priority == "MEDIUM"
        assert "review" in results[0].title.lower()


# ── Repository tests ─────────────────────────────────────────────────────


class TestRecommendationRepository:
    """Tests for RecommendationRepository persistence."""

    async def test_create_and_retrieve_by_id(self) -> None:
        """A created recommendation can be retrieved by ID."""
        db_session = AsyncMock()
        from app.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        rec_id = uuid4()

        rec = MagicMock(spec=PipelineRecommendation)
        rec.id = rec_id

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=rec)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(rec_id)
        assert result is not None
        assert result.id == rec_id

    async def test_get_by_claim_returns_recommendation(self) -> None:
        """get_by_claim returns the recommendation for a given claim."""
        db_session = AsyncMock()
        from app.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        claim_id = uuid4()

        mock_result = AsyncMock()
        expected = MagicMock(spec=PipelineRecommendation)
        expected.source_claim_id = claim_id
        mock_result.scalar_one_or_none = AsyncMock(return_value=expected)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_claim(claim_id)
        assert result is not None
        assert result.source_claim_id == claim_id

    async def test_get_by_creator_returns_list(self) -> None:
        """get_by_creator returns all recommendations for a creator."""
        db_session = AsyncMock()
        from app.repositories.recommendation_repo import RecommendationRepository

        repo = RecommendationRepository(db_session)
        creator_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars = AsyncMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        db_session.execute = AsyncMock(return_value=mock_result)

        results = await repo.get_by_creator(creator_id)
        assert isinstance(results, list)
