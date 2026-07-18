from __future__ import annotations

import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timezone

from app.coordinator import ImportCoordinator
from app.coordinator.exceptions import (
    ConnectedAccountNotFoundError,
    CoordinatorError,
    TokenAcquisitionError,
)
from app.database.session import get_db
from app.jobs.base import ImportType
from app.jobs.factory import ImportJobFactory
from app.models import ConnectedAccount, CreatorProfile, GrowthScore
from app.models.import_run import ImportRunStatus
from app.provider import Provider
from app.repositories.connected_account_repo import ConnectedAccountRepository
from app.repositories.import_run_repo import ImportRunRepository
from app.repositories.finding_repo import FindingRepository
from app.schemas.import_schemas import (
    ChannelImportResponse,
    ErrorResponse,
    ImportStatusResponse,
    VideoImportRequest,
    VideoImportResponse,
)
from app.services.session import get_session_service
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["Import"])


def _build_coordinator(db: AsyncSession) -> ImportCoordinator:
    """Construct an ImportCoordinator with its dependencies."""
    from app.pipeline.orchestrator import run_analysis_pipeline
    from app.models import PipelineEvidence

    async def _run_pipeline(creator_profile_id: UUID, run_id: UUID | None) -> None:
        result = await run_analysis_pipeline(
            db=db,
            creator_profile_id=creator_profile_id,
            source_import_run_id=run_id,
        )
        logger.info(
            "Analysis pipeline completed: "
            "snapshot=%s fv=%s findings=%d evidence=%d claims=%d patterns=%d recs=%d exps=%d",
            result.snapshot_id,
            result.feature_vector_id,
            result.finding_count,
            result.evidence_count,
            result.claim_count,
            result.pattern_count,
            result.recommendation_count,
            result.experiment_count,
        )

        # ── Persist GrowthScore ──────────────────────────────────
        finding_repo = FindingRepository(db)
        findings = await finding_repo.get_by_creator(creator_profile_id)
        if findings:
            deductions = 0
            for f in findings:
                if f.severity == "CRITICAL":
                    deductions += 25
                elif f.severity == "HIGH":
                    deductions += 15
                elif f.severity == "MEDIUM":
                    deductions += 8
                elif f.severity == "INFO":
                    deductions += 3
            score = max(0, min(100, 100 - deductions))
            tier = (
                "Excellent" if score >= 90
                else "Growing Well" if score >= 75
                else "Growing Slowly" if score >= 60
                else "Needs Attention" if score >= 40
                else "At Risk"
            )

            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}
            top = min(findings, key=lambda f: severity_order.get(f.severity, 99))
            summary = top.title if top else None

            evidence_result = await db.execute(
                select(PipelineEvidence)
                .where(PipelineEvidence.creator_profile_id == creator_profile_id)
                .order_by(PipelineEvidence.confidence.desc())
                .limit(1)
            )
            top_evidence = evidence_result.scalar_one_or_none()
            max_conf = top_evidence.confidence if top_evidence else 0.0

            if max_conf >= 0.8:
                pot_low, pot_high = 25, 40
            elif max_conf >= 0.5:
                pot_low, pot_high = 15, 25
            else:
                pot_low, pot_high = 5, 10

            gs = GrowthScore(
                creator_profile_id=creator_profile_id,
                analysis_run_id=run_id,
                score=score,
                tier=tier,
                summary=summary,
                potential_low=pot_low,
                potential_high=pot_high,
                recorded_at=datetime.now(timezone.utc),
            )
            db.add(gs)
            await db.flush()
            logger.info("GrowthScore persisted: score=%d tier=%s", score, tier)

    return ImportCoordinator(
        token_manager=TokenManager(db),
        import_run_repository=ImportRunRepository(db),
        connected_account_repository=ConnectedAccountRepository(db),
        job_factory=ImportJobFactory(db),
        analysis_pipeline_runner=_run_pipeline,
    )


@router.post(
    "/channel",
    response_model=ChannelImportResponse,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def import_channel(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ChannelImportResponse:
    """
    Import a YouTube channel for the authenticated user.

    Looks up the user's creator profile and connected account from the
    session, then triggers a full channel import via ImportCoordinator.
    Returns a structured ChannelImportResponse with success/failure and
    import stats.  Every exception is caught and returned as a structured
    JSON response — the connection is never terminated without a response.
    """
    sess = get_session_service()
    user_id = sess.verify_cookie(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        # ── Look up creator profile ────────────────────────────────
        result = await db.execute(
            select(CreatorProfile).where(
                CreatorProfile.user_id == uid,
                CreatorProfile.platform == "youtube",
            )
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return ChannelImportResponse(
                success=False,
                error="No YouTube creator profile found. "
                "Please connect your YouTube account first.",
            )

        # ── Look up connected account ──────────────────────────────
        result2 = await db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.user_id == uid,
                ConnectedAccount.provider == "google",
            )
        )
        account = result2.scalar_one_or_none()
        if not account:
            return ChannelImportResponse(
                success=False,
                error="No connected Google account found. "
                "Please connect your YouTube account first.",
            )

        # ── Build coordinator and run import ───────────────────────
        coordinator = _build_coordinator(db)
        start = time.monotonic()

        coordinator_result = await coordinator.run(
            creator_profile_id=profile.id,
            connected_account_id=account.id,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        if coordinator_result.status == ImportRunStatus.COMPLETED:
            return ChannelImportResponse(
                success=True,
                imported=coordinator_result.inserted,
                updated=coordinator_result.updated,
                duration_ms=duration_ms,
                error=None,
            )
        else:
            return ChannelImportResponse(
                success=False,
                imported=coordinator_result.inserted,
                updated=coordinator_result.updated,
                duration_ms=duration_ms,
                error="Import did not complete successfully.",
            )

    except ConnectedAccountNotFoundError as e:
        logger.warning("Connected account not found: %s", e)
        return ChannelImportResponse(success=False, error=str(e))
    except TokenAcquisitionError as e:
        logger.warning("Token acquisition failed: %s", e)
        return ChannelImportResponse(
            success=False,
            error=f"Could not authenticate with YouTube: {e}",
        )
    except CoordinatorError as e:
        logger.exception("Coordinator error during channel import")
        return ChannelImportResponse(
            success=False,
            error="Import failed due to an internal error.",
        )
    except Exception as e:
        logger.exception(
            "Unhandled exception during channel import for user=%s", user_id
        )
        return ChannelImportResponse(
            success=False,
            error=f"An unexpected error occurred: {e}",
        )


@router.post(
    "/videos",
    response_model=VideoImportResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def import_videos(
    request: Request,
    body: VideoImportRequest,
    db: AsyncSession = Depends(get_db),
) -> VideoImportResponse:
    sess = get_session_service()
    user_id = sess.verify_cookie(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        coordinator = _build_coordinator(db)
        result = await coordinator.run(
            creator_profile_id=body.creator_profile_id,
            connected_account_id=body.connected_account_id,
            provider=Provider.YOUTUBE,
            import_type=ImportType.VIDEO,
        )
    except ConnectedAccountNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TokenAcquisitionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except CoordinatorError as e:
        logger.exception("Coordinator error during video import")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unhandled exception during video import")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

    assert result.run_id is not None

    return VideoImportResponse(
        status=result.status.value,
        inserted=result.inserted,
        updated=result.updated,
        processed=result.processed,
        duration_ms=result.duration_ms,
        run_id=result.run_id,
    )


@router.get("/status", response_model=ImportStatusResponse)
async def import_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sess = get_session_service()
    user_id = sess.verify_cookie(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        result = await db.execute(
            select(CreatorProfile).where(
                CreatorProfile.user_id == uid,
                CreatorProfile.platform == "youtube",
            )
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return ImportStatusResponse(imported=False, runs=[])

        run_repo = ImportRunRepository(db)
        runs = await run_repo.get_recent_by_profile(profile.id, limit=5)
        completed_with_dates = [
            r for r in runs if r.status.value == "completed" and r.completed_at
        ]
        last = (
            max(completed_with_dates, key=lambda r: r.completed_at)
            if completed_with_dates
            else None
        )

        return ImportStatusResponse(
            imported=any(r.status.value == "completed" for r in runs),
            last_imported_at=last.completed_at if last else None,
            runs=[
                {
                    "id": str(r.id),
                    "status": r.status.value,
                    "videos_imported": r.videos_imported or 0,
                    "videos_failed": r.videos_failed or 0,
                    "error_message": r.error_message,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat()
                    if r.completed_at
                    else None,
                }
                for r in runs
            ],
        )
    except Exception as e:
        logger.exception("Import status failed for user=%s", user_id)
        raise HTTPException(status_code=500, detail=str(e))
