from __future__ import annotations

from app.provider.adapters.base import ProviderAdapter
from app.provider.adapters.youtube_adapter import YouTubeAdapter
from app.provider.enum import Provider


class ProviderAdapterFactory:
    """Returns the correct ProviderAdapter for a given Provider.

    No switch statements outside this factory.
    """

    _registry: dict[Provider, type[ProviderAdapter]] = {
        Provider.YOUTUBE: YouTubeAdapter,
    }

    @classmethod
    def register(cls, provider: Provider, adapter: type[ProviderAdapter]) -> None:
        """Register or override an adapter for the given provider."""
        cls._registry[provider] = adapter

    @classmethod
    def create(cls, provider: Provider) -> ProviderAdapter:
        """Create an adapter instance for the given provider."""
        adapter_cls = cls._registry.get(provider)
        if adapter_cls is None:
            raise ValueError(f"No adapter registered for provider: {provider}")
        return adapter_cls()
