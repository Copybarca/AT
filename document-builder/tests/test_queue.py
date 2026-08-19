import asyncio
from pathlib import Path

import pytest

from document_builder.models import BuildInput, BuildRequest
from document_builder.queue import BuildJob, BuildTaskQueue, SubmitOutcome


def build_input(process_id: int, directory: Path) -> BuildInput:
    request = BuildRequest.model_validate(
        {
            "processId": process_id,
            "bookId": 42,
            "resultCallbackUrl": "/internal/v1/books/42/build-result",
            "document": {"title": "Book", "language": "ru"},
            "elements": [
                {
                    "sequentialNumber": 1,
                    "type": "TEXT",
                    "text": "Body",
                    "style": "BODY",
                }
            ],
        }
    )
    return BuildInput(
        request=request,
        elements=request.elements,
        assets=(),
        job_directory=directory,
        manifest_sha256="sha256:" + str(process_id) * 64,
    )


def job(process_id: int, directory: Path, fingerprint: str) -> BuildJob:
    return BuildJob(build_input(process_id, directory), fingerprint)


@pytest.mark.asyncio
async def test_queue_is_bounded_and_detects_replays(tmp_path: Path) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def handler(_: BuildJob) -> None:
        started.set()
        await release.wait()

    queue = BuildTaskQueue(capacity=1, worker_count=1, handler=handler)
    await queue.start()
    try:
        assert queue.submit(job(1, tmp_path / "one", "one")) is SubmitOutcome.ACCEPTED
        assert queue.submit(job(1, tmp_path / "one", "one")) is SubmitOutcome.DUPLICATE
        assert queue.submit(job(1, tmp_path / "one", "changed")) is SubmitOutcome.CONFLICT
        await asyncio.wait_for(started.wait(), timeout=1)
        assert queue.submit(job(2, tmp_path / "two", "two")) is SubmitOutcome.ACCEPTED
        assert queue.submit(job(3, tmp_path / "three", "three")) is SubmitOutcome.FULL
    finally:
        release.set()
        await queue.stop()


@pytest.mark.asyncio
async def test_failed_build_can_be_retried_without_killing_worker(tmp_path: Path) -> None:
    failed = asyncio.Event()
    completed = asyncio.Event()
    attempts = 0

    async def handler(_: BuildJob) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            failed.set()
            raise RuntimeError("synthetic build failure")
        completed.set()

    queue = BuildTaskQueue(capacity=1, worker_count=1, handler=handler)
    await queue.start()
    try:
        candidate = job(1, tmp_path / "job", "same")
        assert queue.submit(candidate) is SubmitOutcome.ACCEPTED
        await asyncio.wait_for(failed.wait(), timeout=1)
        await asyncio.sleep(0)
        assert queue.submit(candidate) is SubmitOutcome.ACCEPTED
        await asyncio.wait_for(completed.wait(), timeout=1)
    finally:
        await queue.stop()

    assert attempts == 2
