"""ClaimRepository — persistence for PipelineClaim artifacts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PipelineClaim


class ClaimRepository:
    """Database access for PipelineClaim records.

    Append-only — never updated after creation.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, claim: PipelineClaim) -> PipelineClaim:
        self._db.add(claim)
        return claim

    async def create_many(
        self, claims: list[PipelineClaim]
    ) -> list[PipelineClaim]:
        for c in claims:
            self._db.add(c)
        return claims

    async def get_by_id(self, claim_id: UUID) -> PipelineClaim | None:
        result = await self._db.execute(
            select(PipelineClaim).where(PipelineClaim.id == claim_id)
        )
        return result.scalar_one_or_none()

    async def get_by_evidence(
        self, evidence_id: UUID
    ) -> PipelineClaim | None:
        result = await self._db.execute(
            select(PipelineClaim).where(
                PipelineClaim.source_evidence_id == evidence_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_creator(
        self, creator_profile_id: UUID
    ) -> list[PipelineClaim]:
        result = await self._db.execute(
            select(PipelineClaim)
            .where(PipelineClaim.creator_profile_id == creator_profile_id)
            .order_by(PipelineClaim.created_at.desc())
        )
        return list(result.scalars().all())
