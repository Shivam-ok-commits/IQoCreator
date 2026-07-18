from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import ConnectedAccount, CreatorProfile, User
from app.services.session import SessionService, get_session_service


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/youtube.readonly",
]

STATE_COOKIE = "iqo_oauth_state"
STATE_MAX_AGE = 300


class AuthService:
    def __init__(self, session_svc: SessionService) -> None:
        self._session = session_svc

    def get_authorization_url(self, request: Request) -> str:
        state = secrets.token_urlsafe(32)
        request.state._oauth_state = state
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.oauth_redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        import urllib.parse
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def set_state_cookie(self, response: Response, request: Request) -> None:
        state = getattr(request.state, "_oauth_state", None)
        if state:
            response.set_cookie(
                key=STATE_COOKIE,
                value=state,
                max_age=STATE_MAX_AGE,
                httponly=True,
                samesite="lax",
                secure=False,
                path="/",
            )

    def verify_state(self, request: Request) -> bool:
        cookie_state = request.cookies.get(STATE_COOKIE)
        query_state = request.query_params.get("state")
        if not cookie_state or not query_state:
            return False
        return secrets.compare_digest(cookie_state, query_state)

    def clear_state_cookie(self, response: Response) -> None:
        response.delete_cookie(
            key=STATE_COOKIE, path="/", httponly=True, samesite="lax", secure=False
        )

    async def exchange_code(self, code: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.oauth_redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502, detail="Token exchange with Google failed"
                )
            return resp.json()

    async def get_userinfo(self, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502, detail="Failed to fetch user info from Google"
                )
            return resp.json()

    async def get_youtube_channel(self, access_token: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                YOUTUBE_CHANNELS_URL,
                params={"part": "snippet,statistics", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data.get("items", [])
            return items[0] if items else None

    async def upsert_user(
        self, db: AsyncSession, google_sub: str, email: str, name: str | None, avatar: str | None
    ) -> User:
        result = await db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.provider == "google",
                ConnectedAccount.provider_account_id == google_sub,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            result2 = await db.execute(select(User).where(User.id == existing.user_id))
            user = result2.scalar_one_or_none()
            if user:
                return user

        user = User(
            email=email,
            display_name=name,
            avatar_url=avatar,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        return user

    async def upsert_connected_account(
        self,
        db: AsyncSession,
        user_id: Any,
        google_sub: str,
        tokens: dict[str, Any],
    ) -> ConnectedAccount:
        result = await db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.provider == "google",
                ConnectedAccount.provider_account_id == google_sub,
            )
        )
        existing = result.scalar_one_or_none()
        expires_at = None
        if tokens.get("expires_in"):
            expires_at = datetime.now(timezone.utc).replace(tzinfo=None).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=int(tokens["expires_in"])
            )

        if existing:
            existing.access_token = tokens.get("access_token")
            if tokens.get("refresh_token"):
                existing.refresh_token = tokens.get("refresh_token")
            existing.token_expires_at = expires_at
            existing.scope = tokens.get("scope")
            return existing

        account = ConnectedAccount(
            user_id=user_id,
            provider="google",
            provider_account_id=google_sub,
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            token_expires_at=expires_at,
            scope=tokens.get("scope"),
        )
        db.add(account)
        await db.flush()
        return account

    async def upsert_creator_profile(
        self,
        db: AsyncSession,
        user_id: Any,
        channel: dict[str, Any] | None,
        google_sub: str,
    ) -> CreatorProfile:
        platform_creator_id = google_sub
        name = "Unknown Creator"
        handle = None
        description = None
        thumbnail_url = None
        subscriber_count = None
        total_views = None

        if channel:
            snippet = channel.get("snippet", {})
            stats = channel.get("statistics", {})
            platform_creator_id = channel.get("id", google_sub)
            name = snippet.get("title", name)
            handle = snippet.get("customUrl", handle)
            description = snippet.get("description", description)
            thumbnails = snippet.get("thumbnails", {})
            if thumbnails:
                for key in ("maxres", "standard", "high", "medium", "default"):
                    entry = thumbnails.get(key)
                    if entry and isinstance(entry, dict):
                        url = entry.get("url")
                        if url:
                            thumbnail_url = url
                            break
            try:
                subscriber_count = int(stats.get("subscriberCount", 0))
            except (ValueError, TypeError):
                pass
            try:
                total_views = int(stats.get("viewCount", 0))
            except (ValueError, TypeError):
                pass

        result = await db.execute(
            select(CreatorProfile).where(
                CreatorProfile.platform == "youtube",
                CreatorProfile.platform_creator_id == platform_creator_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = name
            existing.handle = handle
            existing.description = description
            existing.thumbnail_url = thumbnail_url
            existing.subscriber_count = subscriber_count
            existing.total_views = total_views
            return existing

        profile = CreatorProfile(
            user_id=user_id,
            platform="youtube",
            platform_creator_id=platform_creator_id,
            name=name,
            handle=handle,
            description=description,
            thumbnail_url=thumbnail_url,
            subscriber_count=subscriber_count,
            total_views=total_views,
        )
        db.add(profile)
        await db.flush()
        return profile
