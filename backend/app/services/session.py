from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import timedelta
from typing import Optional

from fastapi import Request, Response

from app.config import settings


SESSION_COOKIE_NAME = "iqo_session"
SESSION_MAX_AGE = timedelta(days=7).total_seconds()


class SessionService:
    def __init__(self, secret_key: str) -> None:
        self._secret = secret_key.encode("utf-8")

    def _sign(self, value: str) -> str:
        return hmac.new(
            self._secret, value.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def create_cookie(self, response: Response, user_id: str) -> None:
        expires = int(time.time()) + int(SESSION_MAX_AGE)
        payload = f"{user_id}.{expires}"
        sig = self._sign(payload)
        cookie_value = f"{payload}.{sig}"
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=cookie_value,
            max_age=int(SESSION_MAX_AGE),
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
        )

    def verify_cookie(self, request: Request) -> Optional[str]:
        raw = request.cookies.get(SESSION_COOKIE_NAME)
        if not raw:
            return None
        parts = raw.rsplit(".", 1)
        if len(parts) != 2:
            return None
        payload, sig = parts
        expected = self._sign(payload)
        if not hmac.compare_digest(expected, sig):
            return None
        user_id_str, expires_str = payload.rsplit(".", 1)
        try:
            if int(expires_str) < int(time.time()):
                return None
        except ValueError:
            return None
        return user_id_str

    def clear_cookie(self, response: Response) -> None:
        response.delete_cookie(
            key=SESSION_COOKIE_NAME,
            path="/",
            httponly=True,
            samesite="lax",
            secure=False,
        )

    @staticmethod
    def generate_state() -> str:
        return secrets.token_urlsafe(32)

    def sign_state(self, state: str) -> str:
        return self._sign(f"state.{state}")

    def verify_state(self, state: str, signature: str) -> bool:
        expected = self._sign(f"state.{state}")
        return hmac.compare_digest(expected, signature)


_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    global _session_service
    if _session_service is None:
        _session_service = SessionService(settings.secret_key)
    return _session_service
