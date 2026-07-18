from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from app.importers.base import ImportContext, ImportState
from app.models.import_run import ImportRunStatus


class ImportType(str, Enum):
    VIDEO = "video"
    CHANNEL = "channel"


@dataclass(frozen=True)
class ImportCheckpoint:
    next_page_token: str | None = None
    processed_count: int = 0
    total_count: int | None = None


@dataclass(frozen=True)
class ImportResult:
    status: ImportRunStatus
    processed: int = 0
    inserted: int = 0
    updated: int = 0
    duration_ms: int = 0
    checkpoint: ImportCheckpoint | None = None
    run_id: UUID | None = None


class ImportJob(ABC):
    """Abstract execution unit for a single type of import.

    Subclasses implement execute() which uses a ProviderAdapter to
    fetch data and a Repository to persist it.  The job is responsible
    for pagination, batching, checkpoint persistence, and retry.

    One entry point only — the coordinator calls execute() and
    inspects the returned ImportResult.
    """

    @property
    @abstractmethod
    def import_type(self) -> ImportType:
        """Type label used by the coordinator for routing and metrics."""

    @abstractmethod
    async def execute(
        self,
        context: ImportContext,
        state: ImportState,
    ) -> ImportResult:
        """Execute the import.

        Parameters
        ----------
        context : ImportContext
            Immutable identifiers for this run (run_id, profile, etc.).
        state : ImportState
            Mutable state; callers set state.next_page_token to resume
            from a prior checkpoint.  The job updates state as it
            progresses.

        Returns
        -------
        ImportResult
            Frozen result summary.
        """
