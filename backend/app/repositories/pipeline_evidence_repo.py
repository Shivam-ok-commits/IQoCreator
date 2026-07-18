"""PipelineEvidenceRepository — persistence for PipelineEvidence artifacts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PipelineEvidence


class PipelineEvidenceRepository:
    """Database access for PipelineEvidence records.

    Append-only — never updated after creation.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, evidence: PipelineEvidence) -> PipelineEvidence:
        self._db.add(evidence)
        return evidence

    async def create_many(
        self, evidence_list: list[PipelineEvidence]
    ) -> list[PipelineEvidence]:
        for e in evidence_list:
            self._db.add(e)
        return evidence_list

    async def get_by_id(self, evidence_id: UUID) -> PipelineEvidence | None:
        result = await self._db.execute(
            select(PipelineEvidence).where(PipelineEvidence.id == evidence_id)
        )
        return result.scalar_one_or_none()

    async def get_by_finding(
        self, finding_id: UUID
    ) -> PipelineEvidence | None:
        result = await self._db.execute(
            select(PipelineEvidence).where(
                PipelineEvidence.source_finding_id == finding_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_creator(
        self, creator_profile_id: UUID
    ) -> list[PipelineEvidence]:
        result = await self._db.execute(
            select(PipelineEvidence)
            .where(
                PipelineEvidence.creator_profile_id == creator_profile_id
            )
            .order_by(PipelineEvidence.created_at.desc())
        )
        return list(result.scalars().all())
