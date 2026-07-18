from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_import_coordinator
from app.jobs.base import ImportResult
from app.main import app
from app.models.import_run import ImportRunStatus

CREATOR_PROFILE_ID = UUID("11111111-1111-1111-1111-111111111111")
CONNECTED_ACCOUNT_ID = UUID("22222222-2222-2222-2222-222222222222")
RUN_ID = UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def mock_session_service() -> None:
    with patch("app.api.imports.get_session_service") as mock:
        svc = Mock()
        svc.verify_cookie.return_value = str(CREATOR_PROFILE_ID)
        mock.return_value = svc
        yield


@pytest.fixture
def mock_coordinator() -> Mock:
    coordinator = Mock()
    coordinator.run = AsyncMock()
    coordinator.run.return_value = ImportResult(
        status=ImportRunStatus.COMPLETED,
        processed=10,
        inserted=10,
        updated=0,
        duration_ms=1500,
        run_id=RUN_ID,
    )
    return coordinator


@pytest.fixture
def override_deps(mock_coordinator: Mock) -> None:
    app.dependency_overrides[get_import_coordinator] = lambda: mock_coordinator
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(
    mock_session_service: None,
    override_deps: None,
) -> TestClient:
    with TestClient(app) as c:
        yield c
