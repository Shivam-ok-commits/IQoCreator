"""ImportTriggerService — orchestration layer for pipeline stage invocation.

Serves as the single entry point for all import triggers (manual, API,
event, scheduler). Validates inputs, coordinates execution, and returns
trigger results. Contains no business logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from app.models.import_run import ImportRunStatus
from app.pipeline.metrics_collection_stage import (
    MetricsCollectionStage,
    MetricsContext,
)
from app.repositories.connected_account_repo import ConnectedAccountRepository
from app.repositories.creator_profile_repo import CreatorProfileRepository

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    """Origin of an import trigger request."""

    API = "api"
    EVENT = "event"
    SCHEDULE = "schedule"
    MANUAL = "manual"


@dataclass(frozen=True)
class TriggerRequest:
    """Immutable request to trigger a metrics collection run.

    Carries all context needed to identify and execute the collection.
    """

    trigger_type: TriggerType
    creator_profile_id: UUID
    connected_account_id: UUID
    requested_at: datetime
    initiated_by: UUID | None = None


@dataclass(frozen=True)
class TriggerResult:
    """Immutable result of a trigger execution.

    Returns the outcome and the produced artifact identifier.
    """

    status: ImportRunStatus
    snapshot_id: UUID | None = None
    error_message: str | None = None


class ImportTriggerService:
    """Orchestrates a metrics collection run from a trigger request.

    Responsibilities
    -----------------
    1. Validate the creator profile and connected account exist.
    2. Build a MetricsContext and delegate to MetricsCollectionStage.
    3. Return a TriggerResult summarising the outcome.

    Non-responsibilities
    ---------------------
    - Does not fetch data from external APIs.
    - Does not compute or persist metrics.
    - Does not manage retries, scheduling, or event routing.
    - Does not know about downstream stages (FeatureExtraction, etc.).
    """

    def __init__(
        self,
        *,
        creator_profile_repo: CreatorProfileRepository,
        connected_account_repo: ConnectedAccountRepository,
        metrics_stage: MetricsCollectionStage,
    ) -> None:
        self._profile_repo = creator_profile_repo
        self._account_repo = connected_account_repo
        self._metrics_stage = metrics_stage

    async def trigger(
        self,
        request: TriggerRequest,
    ) -> TriggerResult:
        """Execute a metrics collection run.

        Parameters
        ----------
        request : TriggerRequest
            Identifies the creator and accounts to collect metrics for.

        Returns
        -------
        TriggerResult
            Outcome of the collection run.

        Raises
        ------
        ValueError
            If the creator profile does not exist.
        ValueError
            If the connected account does not exist.
        """
        # ── 1. Validate creator profile ───────────────────────────────
        profile = await self._profile_repo.get_by_id(
            request.creator_profile_id
        )
        if profile is None:
            return TriggerResult(
                status=ImportRunStatus.FAILED,
                error_message=(
                    f"Creator profile {request.creator_profile_id} not found"
                ),
            )

        # ── 2. Validate connected account ─────────────────────────────
        account = await self._account_repo.get_by_id(
            request.connected_account_id
        )
        if account is None:
            return TriggerResult(
                status=ImportRunStatus.FAILED,
                error_message=(
                    f"Connected account {request.connected_account_id} not found"
                ),
            )

        # ── 3. Build context and execute ────────────────────────────
        context = MetricsContext(
            creator_profile_id=request.creator_profile_id,
            connected_account_id=request.connected_account_id,
        )

        try:
            snapshot = await self._metrics_stage.execute(context)
            logger.info(
                "Trigger %s completed for creator %s (snapshot=%s)",
                request.trigger_type.value,
                request.creator_profile_id,
                snapshot.id,
            )
            return TriggerResult(
                status=ImportRunStatus.COMPLETED,
                snapshot_id=snapshot.id,
            )
        except Exception:
            logger.exception(
                "Trigger %s failed for creator %s",
                request.trigger_type.value,
                request.creator_profile_id,
            )
            raise
