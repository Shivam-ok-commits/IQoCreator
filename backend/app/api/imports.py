from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.import_service import get_import_service
from app.schemas.import_schemas import ChannelImportResponse, ImportStatusResponse
from app.services.import_service import ImportService
from app.services.session import get_session_service

router = APIRouter(prefix="/api/import", tags=["Import"])


@router.post("/channel", response_model=ChannelImportResponse)
async def import_channel(
    request: Request,
    db: AsyncSession = Depends(get_db),
    import_service: ImportService = Depends(get_import_service),
):
    sess = get_session_service()
    user_id = sess.verify_cookie(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        result = await import_service.import_channel(uid, db)
        return ChannelImportResponse(
            success=result.success,
            imported=result.imported,
            updated=result.updated,
            duration_ms=result.duration_ms,
            error=result.errors[0].message if result.errors else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status", response_model=ImportStatusResponse)
async def import_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    import_service: ImportService = Depends(get_import_service),
):
    sess = get_session_service()
    user_id = sess.verify_cookie(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session")

    return await import_service.get_status(uid, db)
