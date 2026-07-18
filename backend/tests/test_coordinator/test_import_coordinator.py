from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.coordinator import ImportCoordinator
from app.coordinator.exceptions import (
    ConnectedAccountNotFoundError,
    TokenAcquisitionError,
)
from app.importers.base import ImportContext
from app.jobs.base import ImportResult, ImportType
from app.models.import_run import ImportRunStatus
from app.provider import Provider

from .conftest import (
    ACCESS_TOKEN,
    CONNECTED_ACCOUNT_ID,
    CREATOR_PROFILE_ID,
)


class TestSuccessfulOrchestration:
    async def test_returns_completed_result(
        self,
        coordinator: ImportCoordinator,
        mock_job: AsyncMock,
    ) -> None:
        result = await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )
        assert result.status == ImportRunStatus.COMPLETED
        assert result.inserted == 5
        assert result.processed == 5

    async def test_creates_import_run(
        self,
        coordinator: ImportCoordinator,
        mock_run_repo: AsyncMock,
    ) -> None:
        await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )
        mock_run_repo.create.assert_awaited_once_with(
            creator_profile_id=CREATOR_PROFILE_ID,
            source="youtube",
        )

    async def test_calls_job_execute_with_context(
        self,
        coordinator: ImportCoordinator,
        mock_job: AsyncMock,
    ) -> None:
        await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )
        args, _ = mock_job.execute.call_args
        context, state = args
        assert isinstance(context, ImportContext)
        assert context.creator_profile_id == CREATOR_PROFILE_ID
        assert context.connected_account_id == CONNECTED_ACCOUNT_ID
        assert context.provider == "youtube"

    async def test_marks_run_completed(
        self,
        coordinator: ImportCoordinator,
        mock_run_repo: AsyncMock,
    ) -> None:
        await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )
        mock_run_repo.complete.assert_awaited_once()

    async def test_dependencies_invoked_in_order(
        self,
        coordinator: ImportCoordinator,
        mock_account_repo: AsyncMock,
        mock_token_manager: AsyncMock,
        mock_run_repo: AsyncMock,
        mock_job_factory: AsyncMock,
        mock_job: AsyncMock,
    ) -> None:
        await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )
        mock_account_repo.get_by_id.assert_awaited()
        mock_token_manager.get_valid_token.assert_awaited()
        mock_run_repo.get_last_pending_or_running.assert_awaited()
        mock_run_repo.create.assert_awaited()
        mock_job_factory.create.assert_called_once()
        mock_job.execute.assert_awaited()
        mock_run_repo.complete.assert_awaited()


class TestConnectedAccountNotFound:
    async def test_raises_error(
        self,
        coordinator: ImportCoordinator,
        mock_account_repo: AsyncMock,
    ) -> None:
        mock_account_repo.get_by_id.return_value = None
        with pytest.raises(ConnectedAccountNotFoundError):
            await coordinator.run(
                creator_profile_id=CREATOR_PROFILE_ID,
                connected_account_id=CONNECTED_ACCOUNT_ID,
                provider=Provider.YOUTUBE,
                import_type=ImportType.VIDEO,
            )

    async def test_does_not_create_run(
        self,
        coordinator: ImportCoordinator,
        mock_account_repo: AsyncMock,
        mock_run_repo: AsyncMock,
    ) -> None:
        mock_account_repo.get_by_id.return_value = None
        with pytest.raises(ConnectedAccountNotFoundError):
            await coordinator.run(
                creator_profile_id=CREATOR_PROFILE_ID,
                connected_account_id=CONNECTED_ACCOUNT_ID,
                provider=Provider.YOUTUBE,
                import_type=ImportType.VIDEO,
            )
        mock_run_repo.create.assert_not_called()


class TestTokenAcquisitionFailure:
    async def test_raises_error(
        self,
        coordinator: ImportCoordinator,
        mock_token_manager: AsyncMock,
    ) -> None:
        mock_token_manager.get_valid_token.return_value = None
        with pytest.raises(TokenAcquisitionError):
            await coordinator.run(
                creator_profile_id=CREATOR_PROFILE_ID,
                connected_account_id=CONNECTED_ACCOUNT_ID,
                provider=Provider.YOUTUBE,
                import_type=ImportType.VIDEO,
            )

    async def test_does_not_create_run(
        self,
        coordinator: ImportCoordinator,
        mock_token_manager: AsyncMock,
        mock_run_repo: AsyncMock,
    ) -> None:
        mock_token_manager.get_valid_token.return_value = None
        with pytest.raises(TokenAcquisitionError):
            await coordinator.run(
                creator_profile_id=CREATOR_PROFILE_ID,
                connected_account_id=CONNECTED_ACCOUNT_ID,
                provider=Provider.YOUTUBE,
                import_type=ImportType.VIDEO,
            )
        mock_run_repo.create.assert_not_called()


class TestResumeFromExistingRun:
    async def test_creates_state_from_existing_run(
        self,
        coordinator: ImportCoordinator,
        mock_run_repo: AsyncMock,
        mock_job: AsyncMock,
    ) -> None:
        existing_run = AsyncMock()
        existing_run.last_page_token = "next_page_abc"
        existing_run.processed_count = 10
        existing_run.total_count = 50
        mock_run_repo.get_last_pending_or_running.return_value = existing_run

        await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )

        _, state = mock_job.execute.call_args[0]
        assert state.next_page_token == "next_page_abc"
        assert state.processed == 10
        assert state.total == 50

    async def test_creates_new_run_on_resume(
        self,
        coordinator: ImportCoordinator,
        mock_run_repo: AsyncMock,
    ) -> None:
        existing_run = AsyncMock()
        existing_run.last_page_token = "token"
        existing_run.processed_count = 5
        existing_run.total_count = 20
        mock_run_repo.get_last_pending_or_running.return_value = existing_run

        await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )

        mock_run_repo.create.assert_awaited_once()

    async def test_empty_state_when_no_existing_run(
        self,
        coordinator: ImportCoordinator,
        mock_run_repo: AsyncMock,
        mock_job: AsyncMock,
    ) -> None:
        mock_run_repo.get_last_pending_or_running.return_value = None

        await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )

        _, state = mock_job.execute.call_args[0]
        assert state.next_page_token is None
        assert state.processed == 0
        assert state.total == 0

    async def test_empty_state_when_existing_run_has_no_token(
        self,
        coordinator: ImportCoordinator,
        mock_run_repo: AsyncMock,
        mock_job: AsyncMock,
    ) -> None:
        existing_run = AsyncMock()
        existing_run.last_page_token = None
        existing_run.processed_count = 0
        existing_run.total_count = 0
        mock_run_repo.get_last_pending_or_running.return_value = existing_run

        await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )

        _, state = mock_job.execute.call_args[0]
        assert state.next_page_token is None
        assert state.processed == 0


class TestJobExecutionFailure:
    async def test_marks_run_failed_on_exception(
        self,
        coordinator: ImportCoordinator,
        mock_job: AsyncMock,
        mock_run_repo: AsyncMock,
    ) -> None:
        mock_job.execute.side_effect = RuntimeError("Job crashed")
        with pytest.raises(RuntimeError):
            await coordinator.run(
                creator_profile_id=CREATOR_PROFILE_ID,
                connected_account_id=CONNECTED_ACCOUNT_ID,
                provider=Provider.YOUTUBE,
                import_type=ImportType.VIDEO,
            )
        mock_run_repo.fail.assert_awaited_once()

    async def test_marks_run_failed_on_non_completed_result(
        self,
        coordinator: ImportCoordinator,
        mock_job: AsyncMock,
        mock_run_repo: AsyncMock,
    ) -> None:
        mock_job.execute.return_value = ImportResult(
            status=ImportRunStatus.FAILED,
        )
        result = await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )
        assert result.status == ImportRunStatus.FAILED
        mock_run_repo.fail.assert_awaited_once()
        mock_run_repo.complete.assert_not_called()


class TestJobFactoryResolution:
    async def test_factory_creates_correct_job(
        self,
        coordinator: ImportCoordinator,
        mock_job_factory: AsyncMock,
    ) -> None:
        await coordinator.run(
            creator_profile_id=CREATOR_PROFILE_ID,
            connected_account_id=CONNECTED_ACCOUNT_ID,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )
        mock_job_factory.create.assert_called_once_with(
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
            access_token=ACCESS_TOKEN,
        )
