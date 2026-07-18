from __future__ import annotations


class CoordinatorError(Exception):
    """Base exception for all coordinator-level errors."""


class ConnectedAccountNotFoundError(CoordinatorError):
    """Raised when the specified connected account does not exist."""


class TokenAcquisitionError(CoordinatorError):
    """Raised when a valid access token cannot be obtained."""
