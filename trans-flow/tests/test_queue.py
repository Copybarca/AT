from __future__ import annotations

import asyncio

import pytest
from test_worker import command

from trans_flow.queue import SubmitOutcome, TranslationJob, TranslationTaskQueue


@pytest.mark.asyncio
async def test_failed_agent_job_can_be_submitted_again() -> None:
    first_failed = asyncio.Event()
    completed = asyncio.Event()
    calls = 0

    async def handler(_: TranslationJob) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            first_failed.set()
            raise RuntimeError("synthetic")
        completed.set()

    queue = TranslationTaskQueue(capacity=1, worker_count=1, handler=handler)
    job = TranslationJob(command=command(), fingerprint="same")
    await queue.start()
    try:
        assert queue.submit(job) is SubmitOutcome.ACCEPTED
        await asyncio.wait_for(first_failed.wait(), timeout=1)
        for _ in range(100):
            if queue.submit(job) is SubmitOutcome.ACCEPTED:
                break
            await asyncio.sleep(0)
        else:
            raise AssertionError("failed command fingerprint was not released")
        await asyncio.wait_for(completed.wait(), timeout=1)
    finally:
        await queue.stop()

    assert calls == 2
