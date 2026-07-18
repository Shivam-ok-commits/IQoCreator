from __future__ import annotations

from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.coordinator.exceptions import (
    ConnectedAccountNotFoundError,
    CoordinatorError,
    TokenAcquisitionError,
)

from .conftest import CONNECTED_ACCOUNT_ID, CREATOR_PROFILE_ID, RUN_ID


class TestImportVideos:
    URL = "/api/import/videos"
    VALID_BODY = {
        "creator_profile_id": str(CREATOR_PROFILE_ID),
        "connected_account_id": str(CONNECTED_ACCOUNT_ID),
    }

    def test_returns_200_on_success(self, client: TestClient) -> None:
        resp = client.post(self.URL, json=self.VALID_BODY)
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "completed"
        assert data["inserted"] == 10
        assert data["processed"] == 10
        assert data["duration_ms"] == 1500
        assert data["run_id"] == str(RUN_ID)

    def test_returns_401_when_not_authenticated(
        self, client: TestClient, mock_session_service: None
    ) -> None:
        from app.api.imports import get_session_service

        get_session_service().verify_cookie.return_value = None

        resp = client.post(self.URL, json=self.VALID_BODY)
        assert resp.status_code == 401
        assert "detail" in resp.json()

    def test_returns_404_on_connected_account_not_found(
        self, client: TestClient, mock_coordinator: Mock
    ) -> None:
        mock_coordinator.run.side_effect = ConnectedAccountNotFoundError(
            "Account not found"
        )
        resp = client.post(self.URL, json=self.VALID_BODY)
        assert resp.status_code == 404

    def test_returns_401_on_token_acquisition_failure(
        self, client: TestClient, mock_coordinator: Mock
    ) -> None:
        mock_coordinator.run.side_effect = TokenAcquisitionError("Token expired")
        resp = client.post(self.URL, json=self.VALID_BODY)
        assert resp.status_code == 401

    def test_returns_500_on_coordinator_error(
        self, client: TestClient, mock_coordinator: Mock
    ) -> None:
        mock_coordinator.run.side_effect = CoordinatorError("Unexpected error")
        resp = client.post(self.URL, json=self.VALID_BODY)
        assert resp.status_code == 500
        assert "detail" in resp.json()

    def test_returns_422_on_invalid_body(self, client: TestClient) -> None:
        resp = client.post(self.URL, json={})
        assert resp.status_code == 422

    def test_returns_422_on_missing_fields(self, client: TestClient) -> None:
        resp = client.post(
            self.URL, json={"creator_profile_id": str(CREATOR_PROFILE_ID)}
        )
        assert resp.status_code == 422


class TestImportStatus:
    URL = "/api/import/status"

    def test_returns_401_when_not_authenticated(self, client: TestClient) -> None:
        from app.api.imports import get_session_service

        get_session_service().verify_cookie.return_value = None

        resp = client.get(self.URL)
        assert resp.status_code == 401
