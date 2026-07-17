from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ImportError:
    item: str
    message: str


@dataclass
class ChannelImportMetadata:
    channel_name: str | None = None
    handle: str | None = None
    subscriber_count: int | None = None
    video_count: int | None = None
    view_count: int | None = None


@dataclass
class ImportResult:
    success: bool
    imported: int = 0
    updated: int = 0
    failed: int = 0
    duration_ms: int = 0
    errors: list[ImportError] = field(default_factory=list)
    metadata: ChannelImportMetadata | None = None


class BaseImporter(ABC):
    _db: AsyncSession

    @abstractmethod
    async def run(
        self,
        creator_profile_id: UUID,
        access_token: str,
    ) -> ImportResult:
        ...
