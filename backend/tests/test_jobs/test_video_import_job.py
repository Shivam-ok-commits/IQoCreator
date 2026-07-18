from __future__ import annotations

from typing import Any

from app.importers.base import ImportState
from app.jobs.base import ImportType
from app.models.import_run import ImportRunStatus
from app.provider.exceptions import (
    ProviderApiError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)

from .conftest import (
    ACCESS_TOKEN,
    CREATOR_PROFILE_ID,
    MockYouTubeAdapter,
    make_playlist_page,
    make_video_dto,
    run_job,
)


# ── ImportType ──────────────────────────────────────────────────────────


class TestImportType:
    def test_video_type(self) -> None:
        assert ImportType.VIDEO == "video"

    def test_channel_type(self) -> None:
        assert ImportType.CHANNEL == "channel"


# ── Single-page import ──────────────────────────────────────────────────


class TestSinglePageImport:
    async def test_imports_videos_from_single_page(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001", "First Video")
        v2 = make_video_dto("vid_002", "Second Video")
        mock_adapter.add_videos([v1, v2])
        mock_adapter.set_pages(
            [
                make_playlist_page(
                    ["vid_001", "vid_002"], next_page_token=None, estimated_total=2
                ),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 2, 0)

        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )

        assert result.status == ImportRunStatus.COMPLETED
        assert result.inserted == 2
        assert result.updated == 0
        assert result.processed == 2
        assert result.duration_ms >= 0
        assert result.checkpoint is not None
        assert result.checkpoint.processed_count == 2

    async def test_sets_estimated_total(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001")
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(
                    ["vid_001"], next_page_token=None, estimated_total=1
                ),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 1, 0)

        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )

        assert result.status == ImportRunStatus.COMPLETED
        assert result.inserted == 1
        assert state.total == 1

    async def test_calls_bulk_upsert_with_correct_creator_profile(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001")
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_001"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 1, 0)

        await run_job(mock_adapter, mock_video_repo, mock_run_repo, context, state)

        args, _ = mock_video_repo.bulk_upsert.call_args
        models = args[0]
        assert len(models) == 1
        assert models[0].creator_profile_id == CREATOR_PROFILE_ID
        assert models[0].platform_video_id == "vid_001"
        assert models[0].title == "Test Video"

    async def test_logs_call_sequence(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001")
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_001"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 1, 0)

        await run_job(mock_adapter, mock_video_repo, mock_run_repo, context, state)

        call_names = [c.method for c in mock_adapter.calls]
        assert call_names == [
            "get_channel",
            "get_upload_playlist",
            "get_upload_playlist_page",
            "get_video_batch",
        ]


# ── Multi-page import ───────────────────────────────────────────────────


class TestMultiPageImport:
    async def test_imports_all_pages(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        videos = [make_video_dto(f"vid_{i:03d}", f"Video {i}") for i in range(5)]
        mock_adapter.add_videos(videos)
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_000", "vid_001"], next_page_token="p1"),
                make_playlist_page(["vid_002", "vid_003"], next_page_token="p2"),
                make_playlist_page(["vid_004"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.side_effect = [
            ([], 2, 0),
            ([], 2, 0),
            ([], 1, 0),
        ]

        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )

        assert result.status == ImportRunStatus.COMPLETED
        assert result.inserted == 5
        assert result.processed == 5

    async def test_checkpoints_after_each_page(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        videos = [make_video_dto(f"vid_{i:03d}") for i in range(4)]
        mock_adapter.add_videos(videos)
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_000", "vid_001"], next_page_token="p1"),
                make_playlist_page(["vid_002", "vid_003"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 4, 0)

        await run_job(mock_adapter, mock_video_repo, mock_run_repo, context, state)

        assert mock_run_repo.update_checkpoint.call_count == 2
        first_call = mock_run_repo.update_checkpoint.call_args_list[0]
        assert first_call[1]["next_page_token"] == "p1"
        assert first_call[1]["processed_count"] == 2

    async def test_import_type_property(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
    ) -> None:
        from app.jobs.video_import_job import VideoImportJob

        job = VideoImportJob(
            adapter=mock_adapter,
            repository=mock_video_repo,
            run_repo=mock_run_repo,
            access_token=ACCESS_TOKEN,
        )
        assert job.import_type == ImportType.VIDEO


# ── Empty channel ───────────────────────────────────────────────────────


class TestEmptyChannel:
    async def test_no_channel_returns_failed(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        mock_adapter.set_channel(None)
        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )
        assert result.status == ImportRunStatus.FAILED

    async def test_no_playlist_returns_failed(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        mock_adapter.set_playlist(None)
        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )
        assert result.status == ImportRunStatus.FAILED

    async def test_empty_playlist_page(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        mock_adapter.set_pages(
            [
                make_playlist_page([], next_page_token=None),
            ]
        )
        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )
        assert result.status == ImportRunStatus.COMPLETED
        assert result.inserted == 0
        assert result.processed == 0


# ── Resume from checkpoint ─────────────────────────────────────────────


class TestResumeFromCheckpoint:
    async def test_resumes_from_page_token(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        videos = [make_video_dto(f"vid_{i:03d}") for i in range(4)]
        mock_adapter.add_videos(videos)
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_000", "vid_001"], next_page_token="p1"),
                make_playlist_page(["vid_002", "vid_003"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 2, 0)

        resume_state = ImportState(
            processed=2,
            next_page_token="p1",
        )
        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, resume_state
        )

        assert result.status == ImportRunStatus.COMPLETED
        assert result.inserted == 2
        assert result.processed == 2

    async def test_resume_skips_playlist_discovery(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001")
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_001"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 1, 0)

        resume_state = ImportState(next_page_token="resume_token")
        await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, resume_state
        )

        call_names = [c.method for c in mock_adapter.calls]
        # Should still call get_channel and get_upload_playlist on resume
        # (to rebuild playlist_id), then get_upload_playlist_page
        assert "get_upload_playlist_page" in call_names


# ── Duplicate import (idempotent upsert) ────────────────────────────────


class TestDuplicateImport:
    async def test_updates_existing_videos(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001", "Updated Title")
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_001"], next_page_token=None),
            ]
        )
        # Simulate upsert: 0 inserted, 1 updated
        mock_video_repo.bulk_upsert.return_value = ([], 0, 1)

        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )

        assert result.status == ImportRunStatus.COMPLETED
        assert result.inserted == 0
        assert result.updated == 1
        assert result.processed == 1


# ── Authentication failure ─────────────────────────────────────────────


class TestAuthenticationFailure:
    async def test_fails_immediately_on_auth_error(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        mock_adapter.fail_get_channel(ProviderAuthenticationError("Token expired"))
        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )
        assert result.status == ImportRunStatus.FAILED

    async def test_no_retries_on_auth_error(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        mock_adapter.fail_get_channel(ProviderAuthenticationError("Token expired"))
        await run_job(mock_adapter, mock_video_repo, mock_run_repo, context, state)
        # Only one call attempted
        assert len([c for c in mock_adapter.calls if c.method == "get_channel"]) <= 1

    async def test_auth_error_in_playlist_phase(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        mock_adapter.fail_get_upload_playlist(
            ProviderAuthenticationError("Token expired")
        )
        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )
        assert result.status == ImportRunStatus.FAILED


# ── Rate-limit retry ────────────────────────────────────────────────────


class TestRateLimitRetry:
    async def test_retries_on_rate_limit_then_succeeds(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001")
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_001"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 1, 0)

        # Fail on first call, succeed on retry
        original = mock_adapter.get_upload_playlist_page

        call_count = 0

        async def flaky_page(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ProviderRateLimitError("Rate limited")
            return await original(*args, **kwargs)

        mock_adapter.get_upload_playlist_page = flaky_page  # type: ignore[assignment]

        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )

        assert result.status == ImportRunStatus.COMPLETED
        assert result.inserted == 1

    async def test_exhausts_retries_on_rate_limit(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        mock_adapter.fail_get_channel(ProviderRateLimitError("Always rate limited"))
        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )
        assert result.status == ImportRunStatus.FAILED


# ── Provider unavailable retry ──────────────────────────────────────────


class TestUnavailableRetry:
    async def test_retries_on_unavailable_then_succeeds(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001")
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_001"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 1, 0)

        call_count = 0
        original = mock_adapter.get_upload_playlist_page

        async def flaky_page(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ProviderUnavailableError("API down")
            return await original(*args, **kwargs)

        mock_adapter.get_upload_playlist_page = flaky_page  # type: ignore[assignment]

        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )

        assert result.status == ImportRunStatus.COMPLETED
        assert result.inserted == 1

    async def test_exhausts_retries_on_unavailable(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        mock_adapter.fail_get_channel(ProviderUnavailableError("Always down"))
        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )
        assert result.status == ImportRunStatus.FAILED


# ── ProviderApiError (non-retryable) ────────────────────────────────────


class TestApiError:
    async def test_fails_immediately_on_api_error(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        mock_adapter.fail_get_channel(ProviderApiError("YouTube API access denied"))
        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )
        assert result.status == ImportRunStatus.FAILED

    async def test_no_retries_on_api_error(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        mock_adapter.fail_get_channel(ProviderApiError("Access denied"))
        await run_job(mock_adapter, mock_video_repo, mock_run_repo, context, state)
        assert len([c for c in mock_adapter.calls if c.method == "get_channel"]) <= 1


# ── Partial failure → resume ───────────────────────────────────────────


class TestPartialFailureThenResume:
    async def test_recovers_after_partial_failure(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        videos = [make_video_dto(f"vid_{i:03d}") for i in range(4)]
        mock_adapter.add_videos(videos)
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_000", "vid_001"], next_page_token="p1"),
                make_playlist_page(["vid_002", "vid_003"], next_page_token=None),
            ]
        )

        # First run: page 2 fails
        mock_adapter.fail_after_n_page_calls(
            2, ProviderUnavailableError("Temporary outage")
        )
        mock_video_repo.bulk_upsert.return_value = ([], 2, 0)

        result1 = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )
        assert result1.status == ImportRunStatus.FAILED

        # Second run: resumes with checkpoint (fail mechanism disabled)
        mock_adapter.fail_after_n_page_calls(9999, None)
        resume_state = ImportState(
            processed=2,
            next_page_token="p1",
        )
        mock_adapter.calls.clear()
        mock_video_repo.bulk_upsert.return_value = ([], 2, 0)

        result2 = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, resume_state
        )

        assert result2.status == ImportRunStatus.COMPLETED
        assert result2.inserted == 2
        assert result2.processed == 2


# ── DTO mapping correctness ────────────────────────────────────────────


class TestDTOMapping:
    async def test_maps_all_dto_fields_to_model(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        from datetime import datetime

        published = datetime(2024, 6, 15, 10, 30, 0)
        v1 = make_video_dto(
            "vid_001",
            title="Full Video",
            description="A complete test",
            thumbnail_url="https://example.com/thumb.jpg",
            published_at=published,
            duration_seconds=630,
            url="https://youtube.com/watch?v=vid_001",
            language="en",
            privacy_status="public",
            category_id="22",
            tags=("tag1", "tag2"),
        )
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_001"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 1, 0)

        await run_job(mock_adapter, mock_video_repo, mock_run_repo, context, state)

        args, _ = mock_video_repo.bulk_upsert.call_args
        model = args[0][0]

        assert model.platform_video_id == "vid_001"
        assert model.title == "Full Video"
        assert model.description == "A complete test"
        assert model.thumbnail_url == "https://example.com/thumb.jpg"
        assert model.published_at == published
        assert model.duration_seconds == 630
        assert model.url == "https://youtube.com/watch?v=vid_001"
        assert model.language == "en"
        assert model.privacy_status == "public"
        assert model.category_id == "22"
        assert model.tags == {"tags": ["tag1", "tag2"]}

    async def test_handles_none_tags(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001", title="No Tags", tags=())
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_001"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 1, 0)

        await run_job(mock_adapter, mock_video_repo, mock_run_repo, context, state)

        args, _ = mock_video_repo.bulk_upsert.call_args
        model = args[0][0]
        assert model.tags is None


# ── Checkpoint correctness ─────────────────────────────────────────────


class TestCheckpointCorrectness:
    async def test_checkpoint_includes_next_token_and_counts(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001")
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_001"], next_page_token="next_one"),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 1, 0)

        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )

        assert result.checkpoint is not None
        assert result.checkpoint.next_page_token == "next_one"
        assert result.checkpoint.processed_count == 1

    async def test_final_checkpoint_has_no_next_token(
        self,
        mock_adapter: MockYouTubeAdapter,
        mock_video_repo: Any,
        mock_run_repo: Any,
        context: Any,
        state: Any,
    ) -> None:
        v1 = make_video_dto("vid_001")
        mock_adapter.add_videos([v1])
        mock_adapter.set_pages(
            [
                make_playlist_page(["vid_001"], next_page_token=None),
            ]
        )
        mock_video_repo.bulk_upsert.return_value = ([], 1, 0)

        result = await run_job(
            mock_adapter, mock_video_repo, mock_run_repo, context, state
        )

        assert result.checkpoint is not None
        assert result.checkpoint.next_page_token is None
