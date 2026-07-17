from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models import ChannelMetrics, ConnectedAccount, CreatorProfile, User
from app.services.auth import AuthService
from app.services.session import get_session_service

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def get_auth_service() -> AuthService:
    return AuthService(get_session_service())


@router.get("/login")
async def login(
    request: Request,
    auth: AuthService = Depends(get_auth_service),
):
    url = auth.get_authorization_url(request)
    response = Response(status_code=302)
    response.headers["Location"] = url
    auth.set_state_cookie(response, request)
    return response


@router.get("/callback")
async def callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
):
    error = request.query_params.get("error")
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    if not auth.verify_state(request):
        bad = RedirectResponse(url="http://localhost:3000/?error=invalid_state", status_code=302)
        auth.clear_state_cookie(bad)
        return bad

    code = request.query_params.get("code")
    if not code:
        bad = RedirectResponse(url="http://localhost:3000/?error=missing_code", status_code=302)
        auth.clear_state_cookie(bad)
        return bad

    tokens = await auth.exchange_code(code)
    access_token = tokens.get("access_token")
    if not access_token:
        bad = RedirectResponse(url="http://localhost:3000/?error=no_token", status_code=302)
        auth.clear_state_cookie(bad)
        return bad

    userinfo = await auth.get_userinfo(access_token)
    google_sub = userinfo.get("sub")
    if not google_sub:
        bad = RedirectResponse(url="http://localhost:3000/?error=no_subject", status_code=302)
        auth.clear_state_cookie(bad)
        return bad

    email = userinfo.get("email", f"{google_sub}@google.noemail")
    name = userinfo.get("name")
    avatar = userinfo.get("picture")

    user = await auth.upsert_user(db, google_sub, email, name, avatar)
    await auth.upsert_connected_account(db, user.id, google_sub, tokens)

    channel = await auth.get_youtube_channel(access_token)
    await auth.upsert_creator_profile(db, user.id, channel, google_sub)

    sess = get_session_service()
    redirect = RedirectResponse(url="http://localhost:3000/connected", status_code=302)
    sess.create_cookie(redirect, str(user.id))
    auth.clear_state_cookie(redirect)
    return redirect


@router.post("/logout")
async def logout(
    response: Response,
):
    sess = get_session_service()
    sess.clear_cookie(response)
    return {"ok": True}


@router.get("/me")
async def me(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sess = get_session_service()
    user_id = sess.verify_cookie(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    import uuid
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session")

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user or user.is_deleted:
        raise HTTPException(status_code=401, detail="User not found")

    result2 = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.provider == "google",
        )
    )
    account = result2.scalar_one_or_none()

    result3 = await db.execute(
        select(CreatorProfile).where(
            CreatorProfile.user_id == user.id,
            CreatorProfile.platform == "youtube",
        )
    )
    profile = result3.scalar_one_or_none()

    metrics = None
    if profile:
        result4 = await db.execute(
            select(ChannelMetrics)
            .where(ChannelMetrics.creator_profile_id == profile.id)
            .order_by(desc(ChannelMetrics.recorded_at))
            .limit(1)
        )
        metrics = result4.scalar_one_or_none()

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
        },
        "connected_account": {
            "provider": account.provider if account else None,
            "has_token": bool(account and account.access_token),
        },
        "creator_profile": {
            "name": profile.name if profile else None,
            "handle": profile.handle if profile else None,
            "thumbnail_url": profile.thumbnail_url if profile else None,
            "subscriber_count": profile.subscriber_count if profile else None,
            "total_views": profile.total_views if profile else None,
        } if profile else None,
        "channel_metrics": {
            "subscriber_count": metrics.subscriber_count if metrics else None,
            "total_views": metrics.total_views if metrics else None,
            "total_videos": metrics.total_videos if metrics else None,
        } if metrics else None,
    }
