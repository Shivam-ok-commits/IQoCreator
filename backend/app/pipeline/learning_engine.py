"""LearningEngine — convert recommendations into experiment records.

Terminal pipeline stage. Produces experiment records for tracking
recommendation outcomes. No automatic optimization, no AI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from app.models import PipelineExperiment, PipelineRecommendation
from app.repositories.experiment_repo import ExperimentRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LearningContext:
    """Immutable context for experiment generation.

    Carries the recommendation artifacts to convert into experiments.
    """

    recommendations: tuple[PipelineRecommendation, ...]


class LearningEngine:
    """Generates PipelineExperiment artifacts from PipelineRecommendations.

    Responsibilities
    -----------------
    1. For each recommendation, create an experiment record.
    2. Generate deterministic hypotheses from recommendation data.
    3. Persist the resulting PipelineExperiment artifacts.

    Non-responsibilities
    ---------------------
    - Does not evaluate experiment success.
    - Does not modify recommendations.
    - Does not update previous experiments.
    - Does not use AI/LLM.
    """

    def __init__(
        self,
        *,
        experiment_repo: ExperimentRepository,
    ) -> None:
        self._exp_repo = experiment_repo

    async def execute(
        self,
        context: LearningContext,
    ) -> list[PipelineExperiment]:
        """Generate an experiment for each recommendation.

        Parameters
        ----------
        context : LearningContext
            Contains the recommendation artifacts to process.

        Returns
        -------
        list[PipelineExperiment]
            One experiment per recommendation, persisted.
        """
        exps: list[PipelineExperiment] = []

        for rec in context.recommendations:
            exp = self._build_experiment(rec)
            exps.append(exp)

        if exps:
            await self._exp_repo.create_many(exps)
            logger.info(
                "LearningEngine created %d experiment records",
                len(exps),
            )

        return exps

    def _build_experiment(
        self,
        rec: PipelineRecommendation,
    ) -> PipelineExperiment:
        """Build a single PipelineExperiment from a PipelineRecommendation.

        Pure function — no side effects, no database access.
        """
        hypothesis = self._generate_hypothesis(rec)

        return PipelineExperiment(
            id=uuid4(),
            creator_profile_id=rec.creator_profile_id,
            source_recommendation_id=rec.id,
            hypothesis=hypothesis,
            success_metric=rec.success_metric,
            expected_outcome=rec.expected_outcome,
            status="PENDING",
        )

    @staticmethod
    def _generate_hypothesis(
        rec: PipelineRecommendation,
    ) -> str:
        """Generate a deterministic hypothesis from a recommendation.

        Template-based — no free-form text generation.
        """
        return (
            f"Implementing \"{rec.title}\" will lead to "
            f"{rec.expected_outcome or 'improved channel performance'}. "
            f"Success is measured by: "
            f"{rec.success_metric or 'positive metric trends'}."
        )
