"""Token lifecycle management.

TokenManager is the single place where OAuth token refresh happens.
Importers never know about OAuth — they receive a validated token.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.connected_account import ConnectedAccount

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""


class TokenManager:
    """Validates, refreshes, and persists OAuth tokens.

    Usage:
        token = await token_manager.get_valid_token(account)
        if token is None:
            # connection is broken, guide user to reconnect
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_valid_token(self, account: ConnectedAccount) -> str | None:
        """Return a valid access token, refreshing if expired.

        Returns None when the token cannot be refreshed (revoked/expired
        refresh token), signalling that the user must re-authenticate.
        """
        if self._is_expired(account):
            return await self._refresh(account)
        return account.access_token

    async def _refresh(self, account: ConnectedAccount) -> str | None:
        if not account.refresh_token:
            return None

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "refresh_token": account.refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Accept": "application/json"},
            )

        if resp.status_code != 200:
            return None

        data: dict[str, Any] = resp.json()
        new_access_token = data.get("access_token")
        if not new_access_token:
            return None

        account.access_token = new_access_token
        if data.get("expires_in"):
            account.token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=int(data["expires_in"])
            )

        return new_access_token

    @staticmethod
    def _is_expired(account: ConnectedAccount) -> bool:
        if account.token_expires_at is None:
            return False
        return datetime.now(timezone.utc) >= account.token_expires_at
