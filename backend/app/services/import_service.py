from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.importers.base import ImportResult
from app.importers.youtube_importer import YouTubeImporter
from app.models import ConnectedAccount, CreatorProfile, ImportRun, ImportRunStatus


class ImportService:
    async def import_channel(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> ImportResult:
        account_result = await db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.user_id == user_id,
                ConnectedAccount.provider == "google",
            )
        )
        account = account_result.scalar_one_or_none()
        if not account or not account.access_token:
            raise ValueError("No connected account found")

        profile_result = await db.execute(
            select(CreatorProfile).where(
                CreatorProfile.user_id == user_id,
                CreatorProfile.platform == "youtube",
            )
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            raise ValueError("No creator profile found")

        importer = YouTubeImporter()
        importer.bind(db)
        return await importer.run(profile.id, account.access_token)

    async def get_status(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> dict:
        profile_result = await db.execute(
            select(CreatorProfile).where(
                CreatorProfile.user_id == user_id,
                CreatorProfile.platform == "youtube",
            )
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            return {"imported": False, "last_imported_at": None, "runs": []}

        runs_result = await db.execute(
            select(ImportRun)
            .where(ImportRun.creator_profile_id == profile.id)
            .order_by(ImportRun.created_at.desc())
            .limit(5)
        )
        runs = runs_result.scalars().all()

        completed = [r for r in runs if r.status == ImportRunStatus.COMPLETED]
        last = max(completed, key=lambda r: r.completed_at) if completed else None

        return {
            "imported": any(r.status == ImportRunStatus.COMPLETED for r in runs),
            "last_imported_at": last.completed_at.isoformat() if last else None,
            "runs": [
                {
                    "id": str(r.id),
                    "status": r.status.value,
                    "videos_imported": r.videos_imported or 0,
                    "videos_failed": r.videos_failed or 0,
                    "error_message": r.error_message,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in runs
            ],
        }
