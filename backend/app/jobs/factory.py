from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.base import ImportJob, ImportType
from app.jobs.video_import_job import VideoImportJob
from app.provider import Provider
from app.provider.adapters.factory import ProviderAdapterFactory
from app.repositories.import_run_repo import ImportRunRepository
from app.repositories.video_repo import VideoRepository


class ImportJobFactory:
    """Selects and constructs the correct ``ImportJob`` for a provider/type pair.

    Constructor-injected ``db`` is forwarded to each job's repository
    dependencies so the coordinator never touches repositories directly.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def create(
        self,
        provider: Provider,
        import_type: ImportType,
        access_token: str,
    ) -> ImportJob:
        adapter = ProviderAdapterFactory.create(provider)
        if provider == Provider.YOUTUBE and import_type == ImportType.VIDEO:
            return VideoImportJob(
                adapter=adapter,
                repository=VideoRepository(self._db),
                run_repo=ImportRunRepository(self._db),
                access_token=access_token,
            )
        raise ValueError(
            f"No job registered for provider={provider!r} import_type={import_type!r}"
        )
