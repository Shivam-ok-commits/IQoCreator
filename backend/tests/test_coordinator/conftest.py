from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.coordinator.import_coordinator import ImportCoordinator
from app.jobs.base import ImportResult, ImportType
from app.models.import_run import ImportRunStatus

CREATOR_PROFILE_ID = UUID("11111111-1111-1111-1111-111111111111")
CONNECTED_ACCOUNT_ID = UUID("22222222-2222-2222-2222-222222222222")
RUN_ID = UUID("33333333-3333-3333-3333-333333333333")
ACCESS_TOKEN = "test_access_token_456"


@pytest.fixture
def mock_token_manager() -> AsyncMock:
    mgr = AsyncMock()
    mgr.get_valid_token.return_value = ACCESS_TOKEN
    return mgr


@pytest.fixture
def mock_run_repo() -> AsyncMock:
    repo = AsyncMock()
    run = AsyncMock()
    run.id = RUN_ID
    repo.create.return_value = run
    repo.get_last_pending_or_running.return_value = None
    return repo


@pytest.fixture
def mock_account_repo() -> AsyncMock:
    repo = AsyncMock()
    account = AsyncMock()
    account.access_token = ACCESS_TOKEN
    repo.get_by_id.return_value = account
    return repo


@pytest.fixture
def mock_job() -> AsyncMock:
    job = AsyncMock()
    job.import_type = ImportType.VIDEO
    job.execute.return_value = ImportResult(
        status=ImportRunStatus.COMPLETED,
        processed=5,
        inserted=5,
        updated=0,
    )
    return job


@pytest.fixture
def mock_job_factory(mock_job: AsyncMock) -> Mock:
    factory = Mock()
    factory.create.return_value = mock_job
    return factory


@pytest.fixture
def coordinator(
    mock_token_manager: AsyncMock,
    mock_run_repo: AsyncMock,
    mock_account_repo: AsyncMock,
    mock_job_factory: AsyncMock,
) -> ImportCoordinator:
    return ImportCoordinator(
        token_manager=mock_token_manager,
        import_run_repository=mock_run_repo,
        connected_account_repository=mock_account_repo,
        job_factory=mock_job_factory,
    )
