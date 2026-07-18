from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.coordinator import ImportCoordinator
from app.database.session import get_db
from app.jobs.factory import ImportJobFactory
from app.repositories.connected_account_repo import ConnectedAccountRepository
from app.repositories.import_run_repo import ImportRunRepository
from app.services.token_manager import TokenManager


def get_import_coordinator(
    db: AsyncSession = Depends(get_db),
) -> ImportCoordinator:
    return ImportCoordinator(
        token_manager=TokenManager(db),
        import_run_repository=ImportRunRepository(db),
        connected_account_repository=ConnectedAccountRepository(db),
        job_factory=ImportJobFactory(db),
    )
