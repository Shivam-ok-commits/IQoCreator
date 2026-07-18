"""Tests for ImportTriggerService.

Covers: successful trigger, missing creator profile, missing connected
account, stage exception propagation, correct return types.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models import ConnectedAccount, CreatorProfile, MetricSnapshot
from app.models.import_run import ImportRunStatus
from app.pipeline.metrics_collection_stage import (
    MetricsCollectionStage,
)
from app.pipeline.triggers import (
    ImportTriggerService,
    TriggerRequest,
    TriggerResult,
    TriggerType,
)

pytestmark = pytest.mark.asyncio


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def creator_profile_id() -> UUID:
    return uuid4()


@pytest.fixture
def connected_account_id() -> UUID:
    return uuid4()


@pytest.fixture
def sample_request(
    creator_profile_id: UUID,
    connected_account_id: UUID,
) -> TriggerRequest:
    return TriggerRequest(
        trigger_type=TriggerType.MANUAL,
        creator_profile_id=creator_profile_id,
        connected_account_id=connected_account_id,
        requested_at=datetime.now(timezone.utc),
    )


# ── Tests ────────────────────────────────────────────────────────────────


class TestImportTriggerService:
    """Tests for ImportTriggerService."""

    async def test_successful_manual_trigger(
        self,
        creator_profile_id: UUID,
        connected_account_id: UUID,
        sample_request: TriggerRequest,
    ) -> None:
        """A valid trigger produces a completed TriggerResult."""
        # Arrange
        snapshot_id = uuid4()

        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(
            return_value=MagicMock(spec=CreatorProfile)
        )

        account_repo = AsyncMock()
        account_repo.get_by_id = AsyncMock(
            return_value=MagicMock(spec=ConnectedAccount)
        )

        metrics_stage = AsyncMock(spec=MetricsCollectionStage)
        snapshot = MagicMock(spec=MetricSnapshot)
        snapshot.id = snapshot_id
        metrics_stage.execute = AsyncMock(return_value=snapshot)

        service = ImportTriggerService(
            creator_profile_repo=profile_repo,
            connected_account_repo=account_repo,
            metrics_stage=metrics_stage,
        )

        # Act
        result = await service.trigger(sample_request)

        # Assert
        assert isinstance(result, TriggerResult)
        assert result.status == ImportRunStatus.COMPLETED
        assert result.snapshot_id == snapshot_id
        assert result.error_message is None

        # Verify stage was called exactly once
        metrics_stage.execute.assert_awaited_once()

    async def test_missing_creator_profile(
        self,
        connected_account_id: UUID,
        sample_request: TriggerRequest,
    ) -> None:
        """A missing creator profile returns a failed result."""
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=None)

        account_repo = AsyncMock()

        metrics_stage = AsyncMock(spec=MetricsCollectionStage)

        service = ImportTriggerService(
            creator_profile_repo=profile_repo,
            connected_account_repo=account_repo,
            metrics_stage=metrics_stage,
        )

        result = await service.trigger(sample_request)

        assert result.status == ImportRunStatus.FAILED
        assert "not found" in (result.error_message or "")
        assert result.snapshot_id is None

        # Stage should not be called if profile is missing
        metrics_stage.execute.assert_not_awaited()

    async def test_missing_connected_account(
        self,
        creator_profile_id: UUID,
        sample_request: TriggerRequest,
    ) -> None:
        """A missing connected account returns a failed result."""
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(
            return_value=MagicMock(spec=CreatorProfile)
        )

        account_repo = AsyncMock()
        account_repo.get_by_id = AsyncMock(return_value=None)

        metrics_stage = AsyncMock(spec=MetricsCollectionStage)

        service = ImportTriggerService(
            creator_profile_repo=profile_repo,
            connected_account_repo=account_repo,
            metrics_stage=metrics_stage,
        )

        result = await service.trigger(
            TriggerRequest(
                trigger_type=TriggerType.MANUAL,
                creator_profile_id=creator_profile_id,
                connected_account_id=uuid4(),
                requested_at=datetime.now(timezone.utc),
            )
        )

        assert result.status == ImportRunStatus.FAILED
        assert "not found" in (result.error_message or "")
        assert result.snapshot_id is None

        # Stage should not be called if account is missing
        metrics_stage.execute.assert_not_awaited()

    async def test_stage_exception_propagates(
        self,
        sample_request: TriggerRequest,
    ) -> None:
        """When the stage raises, the exception propagates to the caller."""
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(
            return_value=MagicMock(spec=CreatorProfile)
        )

        account_repo = AsyncMock()
        account_repo.get_by_id = AsyncMock(
            return_value=MagicMock(spec=ConnectedAccount)
        )

        metrics_stage = AsyncMock(spec=MetricsCollectionStage)
        metrics_stage.execute = AsyncMock(
            side_effect=ValueError("Something went wrong")
        )

        service = ImportTriggerService(
            creator_profile_repo=profile_repo,
            connected_account_repo=account_repo,
            metrics_stage=metrics_stage,
        )

        with pytest.raises(ValueError, match="Something went wrong"):
            await service.trigger(sample_request)

        metrics_stage.execute.assert_awaited_once()

    async def test_trigger_result_is_correct_type(
        self,
        sample_request: TriggerRequest,
    ) -> None:
        """TriggerResult is always returned (except on exception)."""
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(
            return_value=MagicMock(spec=CreatorProfile)
        )

        account_repo = AsyncMock()
        account_repo.get_by_id = AsyncMock(
            return_value=MagicMock(spec=ConnectedAccount)
        )

        snapshot = MagicMock(spec=MetricSnapshot)
        snapshot.id = uuid4()

        metrics_stage = AsyncMock(spec=MetricsCollectionStage)
        metrics_stage.execute = AsyncMock(return_value=snapshot)

        service = ImportTriggerService(
            creator_profile_repo=profile_repo,
            connected_account_repo=account_repo,
            metrics_stage=metrics_stage,
        )

        result = await service.trigger(sample_request)

        assert isinstance(result, TriggerResult)
        assert isinstance(result.status, ImportRunStatus)
        assert isinstance(result.snapshot_id, UUID)
