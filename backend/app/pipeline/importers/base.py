from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class ImportResult:
    """Standard result returned by every importer."""

    success: bool
    creator_profile_id: UUID
    import_run_id: UUID
    videos_imported: int = 0
    videos_failed: int = 0
    message: str = ""
    error_message: str | None = None


class BaseImporter(ABC):
    """Abstract interface for platform-specific importers.

    Every importer must implement ``run()``, which fetches data
    from the external platform and persists it to the local database.

    The caller is responsible for providing an open database session
    and the connected account token.  The importer handles the rest.
    """

    @abstractmethod
    async def run(
        self,
        creator_profile_id: UUID,
        access_token: str,
    ) -> ImportResult:
        """Execute a full import for the given creator.

        Parameters
        ----------
        creator_profile_id:
            The target creator in the local database.
        access_token:
            OAuth or API token for the external platform.

        Returns
        -------
        ImportResult
            Summary of what was imported.
        """
        ...
