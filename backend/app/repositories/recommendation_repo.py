"""RecommendationRepository — persistence for PipelineRecommendation artifacts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PipelineRecommendation


class RecommendationRepository:
    """Database access for PipelineRecommendation records.

    Append-only — never updated after creation.
    Terminal artifact of the pipeline.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, rec: PipelineRecommendation) -> PipelineRecommendation:
        self._db.add(rec)
        return rec

    async def create_many(
        self, recs: list[PipelineRecommendation]
    ) -> list[PipelineRecommendation]:
        for r in recs:
            self._db.add(r)
        return recs

    async def get_by_id(
        self, rec_id: UUID
    ) -> PipelineRecommendation | None:
        result = await self._db.execute(
            select(PipelineRecommendation).where(
                PipelineRecommendation.id == rec_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_claim(
        self, claim_id: UUID
    ) -> PipelineRecommendation | None:
        result = await self._db.execute(
            select(PipelineRecommendation).where(
                PipelineRecommendation.source_claim_id == claim_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_creator(
        self, creator_profile_id: UUID
    ) -> list[PipelineRecommendation]:
        result = await self._db.execute(
            select(PipelineRecommendation)
            .where(
                PipelineRecommendation.creator_profile_id == creator_profile_id
            )
            .order_by(PipelineRecommendation.created_at.desc())
        )
        return list(result.scalars().all())
