from __future__ import annotations


class ProviderError(Exception):
    """Base exception for all provider adapter errors."""


class ProviderAuthenticationError(ProviderError):
    """Raised when the provider rejects the access token (401)."""


class ProviderRateLimitError(ProviderError):
    """Raised when the provider rate-limits the request (429)."""


class ProviderApiError(ProviderError):
    """Raised when the provider returns an unexpected error (4xx/5xx)."""


class ProviderUnavailableError(ProviderError):
    """Raised when the provider cannot be reached (network error, DNS, etc.)."""
