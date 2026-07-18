from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.importers.base import ImportContext, ImportState
from app.jobs.base import ImportCheckpoint, ImportJob, ImportResult, ImportType
from app.models.import_run import ImportRunStatus
from app.models.video import Video
from app.provider.adapters.base import ProviderAdapter
from app.provider.dto import YouTubeVideoData
from app.provider.exceptions import (
    ProviderApiError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.repositories.import_run_repo import ImportRunRepository
from app.repositories.video_repo import VideoRepository

logger = logging.getLogger(__name__)

# Retry constants
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 2.0
MAX_DELAY_SECONDS = 30.0


class VideoImportJob(ImportJob):
    """Import all videos for a creator's channel.

    Flow
    ----
    1. Resume from checkpoint if ``state.next_page_token`` is set.
    2. Fetch the channel and resolve its upload playlist.
    3. Paginate through every playlist page.
    4. For each page: batch-fetch video metadata, map DTOs to
       ``Video`` models, and ``bulk_upsert`` to the database.
    5. After every completed page, persist a checkpoint to the DB.
    6. Return a frozen ``ImportResult``.
    """

    def __init__(
        self,
        adapter: ProviderAdapter,
        repository: VideoRepository,
        run_repo: ImportRunRepository,
        access_token: str,
    ) -> None:
        self._adapter = adapter
        self._repository = repository
        self._run_repo = run_repo
        self._access_token = access_token

    # ── ImportJob interface ────────────────────────────────────────────

    @property
    def import_type(self) -> ImportType:
        return ImportType.VIDEO

    async def execute(
        self,
        context: ImportContext,
        state: ImportState,
    ) -> ImportResult:
        started_at = datetime.now(timezone.utc)
        checkpoint = ImportCheckpoint(
            next_page_token=state.next_page_token,
            processed_count=state.processed,
            total_count=state.total,
        )

        inserted = 0
        updated = 0
        session_processed = 0

        try:
            # ── 1. Resolve upload playlist ──────────────────────────
            if not state.next_page_token:
                channel = await self._with_retry(
                    "get_channel",
                    self._adapter.get_channel,
                    context,
                    state,
                    self._access_token,
                )
                if channel is None:
                    return self._result(
                        status=ImportRunStatus.FAILED,
                        started_at=started_at,
                        checkpoint=checkpoint,
                    )
                playlist = await self._with_retry(
                    "get_upload_playlist",
                    self._adapter.get_upload_playlist,
                    context,
                    state,
                    self._access_token,
                    channel.channel_id,
                )
                if playlist is None:
                    return self._result(
                        status=ImportRunStatus.FAILED,
                        started_at=started_at,
                        checkpoint=checkpoint,
                    )
                playlist_id = playlist.playlist_id
                caps = self._adapter.capabilities
            else:
                # Resuming — need to rebuild playlist_id from context.
                # The coordinator should store the playlist_id in
                # checkpoint_data for resumption; for now we discover
                # again via get_channel.
                channel = await self._with_retry(
                    "get_channel",
                    self._adapter.get_channel,
                    context,
                    state,
                    self._access_token,
                )
                if channel is None:
                    return self._result(
                        status=ImportRunStatus.FAILED,
                        started_at=started_at,
                        checkpoint=checkpoint,
                    )
                playlist = await self._with_retry(
                    "get_upload_playlist",
                    self._adapter.get_upload_playlist,
                    context,
                    state,
                    self._access_token,
                    channel.channel_id,
                )
                if playlist is None:
                    return self._result(
                        status=ImportRunStatus.FAILED,
                        started_at=started_at,
                        checkpoint=checkpoint,
                    )
                playlist_id = playlist.playlist_id
                caps = self._adapter.capabilities

            # ── 2. Paginate playlist ────────────────────────────────
            page_token: str | None = state.next_page_token
            page_number = 0

            while True:
                page_number += 1
                page = await self._with_retry(
                    "get_upload_playlist_page",
                    self._adapter.get_upload_playlist_page,
                    context,
                    state,
                    self._access_token,
                    playlist_id,
                    page_token,
                )

                if not page.video_ids:
                    page_token = page.next_page_token
                    if page_token is None:
                        break
                    continue

                # Update total estimate if available
                if page.estimated_total is not None and state.total == 0:
                    state.total = page.estimated_total

                # ── 3. Batch-fetch video metadata ───────────────────
                vid_ids = list(page.video_ids)

                if caps.supports_batch_fetch and len(vid_ids) > caps.max_batch_size:
                    batches = [
                        vid_ids[i : i + caps.max_batch_size]
                        for i in range(0, len(vid_ids), caps.max_batch_size)
                    ]
                else:
                    batches = [vid_ids]

                page_inserted = 0
                page_updated = 0

                for batch in batches:
                    dtos = await self._with_retry(
                        "get_video_batch",
                        self._adapter.get_video_batch,
                        context,
                        state,
                        self._access_token,
                        batch,
                    )
                    if not dtos:
                        continue

                    video_models = [
                        self._dto_to_model(dto, context.creator_profile_id)
                        for dto in dtos
                    ]
                    (
                        _,
                        batch_inserted,
                        batch_updated,
                    ) = await self._repository.bulk_upsert(video_models)
                    page_inserted += batch_inserted
                    page_updated += batch_updated

                inserted += page_inserted
                updated += page_updated
                state.processed += len(page.video_ids)
                session_processed += len(page.video_ids)

                # ── 4. Checkpoint after every page ──────────────────
                page_token = page.next_page_token
                checkpoint = ImportCheckpoint(
                    next_page_token=page_token,
                    processed_count=state.processed,
                    total_count=state.total,
                )

                await self._run_repo.update_checkpoint(
                    run_id=context.import_run_id,
                    next_page_token=page_token,
                    processed_count=state.processed,
                    total_count=state.total if state.total else None,
                )

                if page_token is None:
                    break

            status = ImportRunStatus.COMPLETED

        except ProviderAuthenticationError:
            status = ImportRunStatus.FAILED
        except ProviderApiError:
            status = ImportRunStatus.FAILED
        except Exception:
            logger.exception("Unhandled error in VideoImportJob")
            status = ImportRunStatus.FAILED

        return self._result(
            status=status,
            started_at=started_at,
            inserted=inserted,
            updated=updated,
            processed=session_processed,
            checkpoint=checkpoint,
        )

    # ── Internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _dto_to_model(dto: YouTubeVideoData, creator_profile_id: UUID) -> Video:
        tags_value: dict[str, Any] | None = None
        if dto.tags:
            tags_value = {"tags": list(dto.tags)}

        return Video(
            creator_profile_id=creator_profile_id,
            platform_video_id=dto.video_id,
            title=dto.title,
            description=dto.description,
            thumbnail_url=dto.thumbnail_url,
            published_at=dto.published_at,
            duration_seconds=dto.duration_seconds,
            url=dto.url,
            language=dto.language,
            privacy_status=dto.privacy_status,
            category_id=dto.category_id,
            tags=tags_value,
        )

    @staticmethod
    def _result(
        status: ImportRunStatus,
        started_at: datetime,
        inserted: int = 0,
        updated: int = 0,
        processed: int = 0,
        checkpoint: ImportCheckpoint | None = None,
    ) -> ImportResult:
        duration_ms = int(
            (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
        )
        return ImportResult(
            status=status,
            processed=processed,
            inserted=inserted,
            updated=updated,
            duration_ms=duration_ms,
            checkpoint=checkpoint,
        )

    async def _with_retry(
        self,
        operation: str,
        coro: Any,
        context: ImportContext,
        state: ImportState,
        *args: Any,
    ) -> Any:
        """Execute *coro* with typed-exception-aware retry logic.

        Retry policy
        ------------
        ProviderUnavailableError  → retry (exponential backoff)
        ProviderRateLimitError    → retry (gradual backoff)
        ProviderAuthenticationError → fail immediately
        ProviderApiError          → fail immediately
        """
        last_exc: Exception | None = None
        attempt = 0

        while attempt <= MAX_RETRIES:
            if attempt > 0:
                delay = min(
                    BASE_DELAY_SECONDS * (2 ** (attempt - 1)), MAX_DELAY_SECONDS
                )
                logger.info(
                    "Retrying %s in %.1fs (attempt %d/%d)",
                    operation,
                    delay,
                    attempt,
                    MAX_RETRIES,
                )
                await asyncio.sleep(delay)

            try:
                return await coro(*args)
            except ProviderAuthenticationError:
                raise
            except ProviderApiError:
                raise
            except ProviderRateLimitError as exc:
                state.retries += 1
                last_exc = exc
                if attempt >= MAX_RETRIES:
                    raise
            except ProviderUnavailableError as exc:
                state.retries += 1
                last_exc = exc
                if attempt >= MAX_RETRIES:
                    raise
            finally:
                attempt += 1

        raise last_exc  # type: ignore[misc]
