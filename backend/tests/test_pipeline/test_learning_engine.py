"""Tests for LearningEngine.

Covers: successful experiment generation, replay/idempotency,
historical persistence, empty recommendations list, repository
queries, experiment fields verified.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models import PipelineExperiment, PipelineRecommendation
from app.models.pipeline_experiment import PipelineExperimentStatus
from app.pipeline.learning_engine import LearningContext, LearningEngine

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_rec(
    rec_id: UUID | None = None,
    priority: str = "HIGH",
    title: str = "Increase upload cadence",
    expected_outcome: str = "Improved subscriber growth",
    success_metric: str = "Upload frequency > 0.14/week",
) -> PipelineRecommendation:
    r = MagicMock(spec=PipelineRecommendation)
    r.id = rec_id or uuid4()
    r.creator_profile_id = uuid4()
    r.source_claim_id = uuid4()
    r.priority = priority
    r.title = title
    r.expected_outcome = expected_outcome
    r.success_metric = success_metric
    return r


# ── Tests ────────────────────────────────────────────────────────────────


class TestLearningEngine:
    """Tests for LearningEngine."""

    async def test_successful_experiment_generation(self) -> None:
        """A recommendation produces an experiment with all required fields."""
        rec = _make_rec()
        exp_repo = AsyncMock()
        exp_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = LearningEngine(experiment_repo=exp_repo)
        context = LearningContext(recommendations=(rec,))

        results = await engine.execute(context)

        assert len(results) == 1
        exp = results[0]
        assert exp.source_recommendation_id == rec.id
        assert exp.creator_profile_id == rec.creator_profile_id
        assert exp.status == PipelineExperimentStatus.PENDING
        assert exp.hypothesis is not None
        assert exp.success_metric == rec.success_metric
        assert exp.expected_outcome == rec.expected_outcome

        exp_repo.create_many.assert_awaited_once()

    async def test_empty_recommendation_list(self) -> None:
        """No recommendations produces no experiments."""
        exp_repo = AsyncMock()
        exp_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = LearningEngine(experiment_repo=exp_repo)
        context = LearningContext(recommendations=())

        results = await engine.execute(context)
        assert len(results) == 0
        exp_repo.create_many.assert_not_awaited()

    async def test_multiple_recs_produce_multiple_experiments(self) -> None:
        """Multiple recommendations produce one experiment each."""
        recs = [
            _make_rec(title="Increase upload cadence"),
            _make_rec(title="Improve audience retention"),
            _make_rec(title="Increase long-form balance"),
        ]

        exp_repo = AsyncMock()
        exp_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = LearningEngine(experiment_repo=exp_repo)
        context = LearningContext(recommendations=tuple(recs))

        results = await engine.execute(context)
        assert len(results) == 3
        exp_repo.create_many.assert_awaited_once()

    async def test_replay_produces_identical_hypotheses(self) -> None:
        """Same recommendation produces identical hypothesis text."""
        rec = _make_rec()

        exp_repo = AsyncMock()
        exp_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = LearningEngine(experiment_repo=exp_repo)
        context = LearningContext(recommendations=(rec,))

        results1 = await engine.execute(context)
        results2 = await engine.execute(context)

        assert len(results1) == len(results2)
        assert results1[0].hypothesis == results2[0].hypothesis
        assert results1[0].status == results2[0].status
        assert results1[0].success_metric == results2[0].success_metric

    async def test_hypothesis_includes_title_and_outcome(self) -> None:
        """Hypothesis text references the recommendation title and outcome."""
        rec = _make_rec(
            title="Increase upload cadence",
            expected_outcome="Improved subscriber growth and channel visibility",
            success_metric="Upload frequency > 0.14 videos/week",
        )

        exp_repo = AsyncMock()
        exp_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = LearningEngine(experiment_repo=exp_repo)
        context = LearningContext(recommendations=(rec,))

        results = await engine.execute(context)
        hypothesis = results[0].hypothesis

        assert "Increase upload cadence" in hypothesis
        assert "subscriber growth" in hypothesis
        assert "Upload frequency" in hypothesis

    async def test_experiment_fields_verified(self) -> None:
        """All experiment fields match the source recommendation."""
        rec = _make_rec(
            priority="HIGH",
            title="Test recommendation",
            expected_outcome="Test outcome",
            success_metric="Test metric",
        )

        exp_repo = AsyncMock()
        exp_repo.create_many = AsyncMock(side_effect=lambda x: x)

        engine = LearningEngine(experiment_repo=exp_repo)
        context = LearningContext(recommendations=(rec,))

        results = await engine.execute(context)
        exp = results[0]

        assert exp.source_recommendation_id == rec.id
        assert exp.expected_outcome == "Test outcome"
        assert exp.success_metric == "Test metric"
        assert exp.status == PipelineExperimentStatus.PENDING
        assert rec.title in exp.hypothesis


# ── Repository tests ─────────────────────────────────────────────────────


class TestExperimentRepository:
    """Tests for ExperimentRepository persistence."""

    async def test_create_and_retrieve_by_id(self) -> None:
        """A created experiment can be retrieved by ID."""
        db_session = AsyncMock()
        from app.repositories.experiment_repo import ExperimentRepository

        repo = ExperimentRepository(db_session)
        exp_id = uuid4()

        exp = MagicMock(spec=PipelineExperiment)
        exp.id = exp_id

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=exp)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_id(exp_id)
        assert result is not None
        assert result.id == exp_id

    async def test_get_by_recommendation_returns_experiment(self) -> None:
        """get_by_recommendation returns the experiment for a given rec."""
        db_session = AsyncMock()
        from app.repositories.experiment_repo import ExperimentRepository

        repo = ExperimentRepository(db_session)
        rec_id = uuid4()

        mock_result = AsyncMock()
        expected = MagicMock(spec=PipelineExperiment)
        expected.source_recommendation_id = rec_id
        mock_result.scalar_one_or_none = AsyncMock(return_value=expected)
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_recommendation(rec_id)
        assert result is not None
        assert result.source_recommendation_id == rec_id

    async def test_get_by_creator_returns_list(self) -> None:
        """get_by_creator returns all experiments for a creator."""
        db_session = AsyncMock()
        from app.repositories.experiment_repo import ExperimentRepository

        repo = ExperimentRepository(db_session)
        creator_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars = AsyncMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        db_session.execute = AsyncMock(return_value=mock_result)

        results = await repo.get_by_creator(creator_id)
        assert isinstance(results, list)
