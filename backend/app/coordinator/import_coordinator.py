from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.coordinator.exceptions import (
    ConnectedAccountNotFoundError,
    TokenAcquisitionError,
)
from app.importers.base import ImportContext, ImportState
from app.jobs.base import ImportResult, ImportType
from app.jobs.factory import ImportJobFactory
from app.models.import_run import ImportRunStatus
from app.provider import Provider
from app.repositories.connected_account_repo import ConnectedAccountRepository
from app.repositories.import_run_repo import ImportRunRepository
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

# Callable that runs the analysis pipeline after a successful import.
# Signature: (creator_profile_id, run_id) -> None
AnalysisPipelineRunner = Callable[
    [UUID, UUID | None], Coroutine[Any, Any, None]
]


class ImportCoordinator:
    """Orchestrates a single import lifecycle.

    Responsibilities
    -----------------
    1. Load the connected account and acquire an access token.
    2. Check for a prior incomplete run (resume support).
    3. Create a new ``ImportRun``.
    4. Build an ``ImportContext``.
    5. Resolve the correct ``ImportJob`` via ``ImportJobFactory``.
    6. Execute the job.
    7. Persist the final status (COMPLETED or FAILED).
    8. If the import completed successfully, invoke the analysis
       pipeline runner (if provided).

    Non-responsibilities
    ---------------------
    - Does **not** call YouTube HTTP endpoints.
    - Does **not** know about playlists, page tokens, or batching.
    - Does **not** transform DTOs or parse provider JSON.
    - Does **not** contain provider-specific retry logic.
    """

    def __init__(
        self,
        *,
        token_manager: TokenManager,
        import_run_repository: ImportRunRepository,
        connected_account_repository: ConnectedAccountRepository,
        job_factory: ImportJobFactory,
        analysis_pipeline_runner: AnalysisPipelineRunner | None = None,
    ) -> None:
        self._token_manager = token_manager
        self._run_repo = import_run_repository
        self._account_repo = connected_account_repository
        self._job_factory = job_factory
        self._analysis_runner = analysis_pipeline_runner

    async def run(
        self,
        *,
        creator_profile_id: UUID,
        connected_account_id: UUID,
        provider: Provider,
        import_type: ImportType,
    ) -> ImportResult:
        # ── 1. Load connected account ────────────────────────────────
        account = await self._account_repo.get_by_id(connected_account_id)
        if account is None:
            raise ConnectedAccountNotFoundError(
                f"Connected account {connected_account_id} not found"
            )

        # ── 2. Acquire access token ──────────────────────────────────
        access_token = await self._token_manager.get_valid_token(account)
        if access_token is None:
            raise TokenAcquisitionError(
                f"Failed to acquire token for account {connected_account_id}"
            )

        # ── 3. Check for existing pending/running run (resume) ──────
        state = ImportState()
        existing = await self._run_repo.get_last_pending_or_running(creator_profile_id)
        if existing is not None and existing.last_page_token is not None:
            state.next_page_token = existing.last_page_token
            state.processed = existing.processed_count or 0
            state.total = existing.total_count or 0

        # ── 4. Create ImportRun ──────────────────────────────────────
        run = await self._run_repo.create(
            creator_profile_id=creator_profile_id,
            source=provider.value,
        )

        # ── 5. Build ImportContext ───────────────────────────────────
        context = ImportContext(
            import_run_id=run.id,
            creator_profile_id=creator_profile_id,
            connected_account_id=connected_account_id,
            provider=provider.value,
            started_at=datetime.now(timezone.utc),
        )

        # ── 6. Resolve ImportJob ─────────────────────────────────────
        job = self._job_factory.create(
            provider=provider,
            import_type=import_type,
            access_token=access_token,
        )

        # ── 7. Execute job ───────────────────────────────────────────
        try:
            result = await job.execute(context, state)
        except Exception:
            await self._run_repo.fail(run, "Import failed with unexpected error")
            raise

        # ── 8. Persist final status ──────────────────────────────────
        if result.status == ImportRunStatus.COMPLETED:
            await self._run_repo.complete(run)
            # ── 9. Trigger analysis pipeline ─────────────────────────
            if self._analysis_runner is not None:
                try:
                    await self._analysis_runner(
                        creator_profile_id,
                        run.id,
                    )
                except Exception:
                    logger.exception(
                        "Analysis pipeline failed after import %s for creator %s",
                        run.id, creator_profile_id,
                    )
        else:
            await self._run_repo.fail(run, "Import did not complete successfully")

        return replace(result, run_id=run.id)
