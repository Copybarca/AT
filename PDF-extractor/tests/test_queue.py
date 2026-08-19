import asyncio
from pathlib import Path

import pytest

from pdf_extractor.models import ExtractionCommand
from pdf_extractor.queue import (
    ExtractionJob,
    ExtractionTaskQueue,
    SubmitOutcome,
)
from pdf_extractor.settings import FragmentationSettings


def job(process_id: int, fingerprint: str) -> ExtractionJob:
    return ExtractionJob(
        command=ExtractionCommand(
            process_id=process_id,
            book_id=42,
            source_sha256=None,
        ),
        pdf_path=Path(f"/tmp/{process_id}.pdf"),
        fragmentation=FragmentationSettings(),
        fingerprint=fingerprint,
        temp_directory=Path(f"/tmp/job-{process_id}"),
    )


@pytest.mark.asyncio
async def test_queue_rejects_conflict_and_accepts_identical_replay() -> None:
    release = asyncio.Event()

    async def handler(_: ExtractionJob) -> None:
        await release.wait()

    queue = ExtractionTaskQueue(capacity=2, worker_count=1, handler=handler)
    await queue.start()
    try:
        assert queue.submit(job(1, "same")) is SubmitOutcome.ACCEPTED
        assert queue.submit(job(1, "same")) is SubmitOutcome.DUPLICATE
        assert queue.submit(job(1, "different")) is SubmitOutcome.CONFLICT
    finally:
        release.set()
        await queue.stop()


@pytest.mark.asyncio
async def test_queue_has_a_hard_bounded_capacity() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def handler(_: ExtractionJob) -> None:
        started.set()
        await release.wait()

    queue = ExtractionTaskQueue(capacity=1, worker_count=1, handler=handler)
    await queue.start()
    try:
        assert queue.submit(job(1, "one")) is SubmitOutcome.ACCEPTED
        await asyncio.wait_for(started.wait(), timeout=1)
        assert queue.submit(job(2, "two")) is SubmitOutcome.ACCEPTED
        assert queue.submit(job(3, "three")) is SubmitOutcome.FULL
    finally:
        release.set()
        await queue.stop()


@pytest.mark.asyncio
async def test_failed_job_does_not_kill_worker_and_can_be_retried() -> None:
    first_failed = asyncio.Event()
    second_finished = asyncio.Event()
    attempts = 0

    async def handler(_: ExtractionJob) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            first_failed.set()
            raise RuntimeError("synthetic failure")
        second_finished.set()

    queue = ExtractionTaskQueue(capacity=1, worker_count=1, handler=handler)
    await queue.start()
    try:
        assert queue.submit(job(1, "retryable")) is SubmitOutcome.ACCEPTED
        await asyncio.wait_for(first_failed.wait(), timeout=1)
        await asyncio.sleep(0)

        assert queue.submit(job(1, "retryable")) is SubmitOutcome.ACCEPTED
        await asyncio.wait_for(second_finished.wait(), timeout=1)
    finally:
        await queue.stop()

    assert attempts == 2
