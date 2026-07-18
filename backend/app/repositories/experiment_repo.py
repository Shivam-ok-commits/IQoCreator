"""ExperimentRepository — persistence for PipelineExperiment artifacts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PipelineExperiment


class ExperimentRepository:
    """Database access for PipelineExperiment records.

    Append-only — never updated after creation.
    Outcomes are tracked via separate result records.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, exp: PipelineExperiment) -> PipelineExperiment:
        self._db.add(exp)
        return exp

    async def create_many(
        self, exps: list[PipelineExperiment]
    ) -> list[PipelineExperiment]:
        for e in exps:
            self._db.add(e)
        return exps

    async def get_by_id(
        self, exp_id: UUID
    ) -> PipelineExperiment | None:
        result = await self._db.execute(
            select(PipelineExperiment).where(
                PipelineExperiment.id == exp_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_recommendation(
        self, rec_id: UUID
    ) -> PipelineExperiment | None:
        result = await self._db.execute(
            select(PipelineExperiment).where(
                PipelineExperiment.source_recommendation_id == rec_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_creator(
        self, creator_profile_id: UUID
    ) -> list[PipelineExperiment]:
        result = await self._db.execute(
            select(PipelineExperiment)
            .where(
                PipelineExperiment.creator_profile_id == creator_profile_id
            )
            .order_by(PipelineExperiment.created_at.desc())
        )
        return list(result.scalars().all())
