"""FindingRepository — persistence for Finding artifacts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Finding


class FindingRepository:
    """Database access for Finding records.

    Findings are append-only — never updated after creation.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, finding: Finding) -> Finding:
        """Persist a new Finding."""
        self._db.add(finding)
        return finding

    async def create_many(self, findings: list[Finding]) -> list[Finding]:
        """Persist multiple findings in a single batch."""
        for f in findings:
            self._db.add(f)
        return findings

    async def get_by_id(self, finding_id: UUID) -> Finding | None:
        result = await self._db.execute(
            select(Finding).where(Finding.id == finding_id)
        )
        return result.scalar_one_or_none()

    async def get_by_feature_vector(
        self, feature_vector_id: UUID
    ) -> list[Finding]:
        result = await self._db.execute(
            select(Finding)
            .where(Finding.source_feature_vector_id == feature_vector_id)
        )
        return list(result.scalars().all())

    async def get_by_creator(
        self, creator_profile_id: UUID
    ) -> list[Finding]:
        result = await self._db.execute(
            select(Finding)
            .where(Finding.creator_profile_id == creator_profile_id)
            .order_by(Finding.created_at.desc())
        )
        return list(result.scalars().all())
