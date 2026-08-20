from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum

from trans_flow.models import TranslationCommand

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TranslationJob:
    command: TranslationCommand
    fingerprint: str


class SubmitOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    FULL = "FULL"


JobHandler = Callable[[TranslationJob], Awaitable[None]]


class TranslationTaskQueue:
    def __init__(self, *, capacity: int, worker_count: int, handler: JobHandler) -> None:
        if capacity < 1 or worker_count < 1:
            raise ValueError("Queue capacity and worker count must be positive")
        self._queue: asyncio.Queue[TranslationJob] = asyncio.Queue(maxsize=capacity)
        self._worker_count = worker_count
        self._handler = handler
        self._fingerprints: dict[tuple[int, int], str] = {}
        self._workers: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        if self._workers:
            return
        self._workers = [
            asyncio.create_task(self._run_worker(), name=f"translation-worker-{index}")
            for index in range(self._worker_count)
        ]

    async def stop(self) -> None:
        if not self._workers:
            return
        await self._queue.join()
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    def submit(self, job: TranslationJob) -> SubmitOutcome:
        key = (job.command.process_id, job.command.segment_id)
        existing = self._fingerprints.get(key)
        if existing is not None:
            return (
                SubmitOutcome.DUPLICATE
                if existing == job.fingerprint
                else SubmitOutcome.CONFLICT
            )
        if self._queue.full():
            return SubmitOutcome.FULL
        self._fingerprints[key] = job.fingerprint
        self._queue.put_nowait(job)
        return SubmitOutcome.ACCEPTED

    async def _run_worker(self) -> None:
        while True:
            job = await self._queue.get()
            key = (job.command.process_id, job.command.segment_id)
            try:
                await self._handler(job)
            except asyncio.CancelledError:
                raise
            except Exception:
                # A command may be submitted again when callback delivery failed.
                self._fingerprints.pop(key, None)
                _LOGGER.exception(
                    "Translation job failed",
                    extra={
                        "processId": job.command.process_id,
                        "segmentId": job.command.segment_id,
                    },
                )
            finally:
                self._queue.task_done()
