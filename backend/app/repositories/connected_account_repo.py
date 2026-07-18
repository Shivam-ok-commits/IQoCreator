from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connected_account import ConnectedAccount


class ConnectedAccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, account_id: UUID) -> ConnectedAccount | None:
        result = await self._db.execute(
            select(ConnectedAccount).where(ConnectedAccount.id == account_id)
        )
        return result.scalar_one_or_none()
