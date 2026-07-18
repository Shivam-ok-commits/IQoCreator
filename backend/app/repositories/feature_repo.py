"""FeatureRepository — persistence for MetricFeatureVector artifacts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MetricFeatureVector


class FeatureRepository:
    """Database access for MetricFeatureVector records.

    Handles idempotent upsert and historical lookup.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, vector: MetricFeatureVector) -> MetricFeatureVector:
        """Persist a MetricFeatureVector.

        Uses PostgreSQL INSERT … ON CONFLICT on source_snapshot_id
        to guarantee idempotency.
        """
        stmt = pg_insert(MetricFeatureVector).values(
            {
                "id": vector.id,
                "creator_profile_id": vector.creator_profile_id,
                "source_snapshot_id": vector.source_snapshot_id,
                "features": vector.features,
                "feature_schema_version": vector.feature_schema_version,
                "version": vector.version,
            }
        )

        do_update = stmt.on_conflict_do_update(
            index_elements=["source_snapshot_id"],
            set_={
                "features": stmt.excluded.features,
                "feature_schema_version": stmt.excluded.feature_schema_version,
                "version": stmt.excluded.version,
            },
        )

        await self._db.execute(do_update)
        return vector

    async def get_by_id(self, vector_id: UUID) -> MetricFeatureVector | None:
        result = await self._db.execute(
            select(MetricFeatureVector).where(
                MetricFeatureVector.id == vector_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_snapshot(
        self, snapshot_id: UUID
    ) -> MetricFeatureVector | None:
        result = await self._db.execute(
            select(MetricFeatureVector).where(
                MetricFeatureVector.source_snapshot_id == snapshot_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_creator(
        self, creator_profile_id: UUID
    ) -> list[MetricFeatureVector]:
        result = await self._db.execute(
            select(MetricFeatureVector)
            .where(
                MetricFeatureVector.creator_profile_id == creator_profile_id
            )
            .order_by(MetricFeatureVector.computed_at.desc())
        )
        return list(result.scalars().all())

    async def get_latest_by_creator(
        self, creator_profile_id: UUID
    ) -> MetricFeatureVector | None:
        result = await self._db.execute(
            select(MetricFeatureVector)
            .where(
                MetricFeatureVector.creator_profile_id == creator_profile_id
            )
            .order_by(MetricFeatureVector.computed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
