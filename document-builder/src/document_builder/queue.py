from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum

from document_builder.models import BuildInput

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BuildJob:
    build_input: BuildInput
    fingerprint: str

    @property
    def process_id(self) -> int:
        return self.build_input.request.process_id


class SubmitOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    FULL = "FULL"


JobHandler = Callable[[BuildJob], Awaitable[None]]


class BuildTaskQueue:
    def __init__(
        self,
        *,
        capacity: int,
        worker_count: int,
        handler: JobHandler,
    ) -> None:
        if capacity < 1:
            raise ValueError("Queue capacity must be positive")
        if worker_count < 1:
            raise ValueError("Worker count must be positive")
        self._queue: asyncio.Queue[BuildJob] = asyncio.Queue(maxsize=capacity)
        self._worker_count = worker_count
        self._handler = handler
        self._fingerprints: dict[int, str] = {}
        self._workers: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        if self._workers:
            return
        self._workers = [
            asyncio.create_task(self._run_worker(), name=f"build-worker-{index}")
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

    def submit(self, job: BuildJob) -> SubmitOutcome:
        existing = self._fingerprints.get(job.process_id)
        if existing is not None:
            return (
                SubmitOutcome.DUPLICATE
                if existing == job.fingerprint
                else SubmitOutcome.CONFLICT
            )
        if self._queue.full():
            return SubmitOutcome.FULL
        self._fingerprints[job.process_id] = job.fingerprint
        self._queue.put_nowait(job)
        return SubmitOutcome.ACCEPTED

    async def _run_worker(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                await self._handler(job)
            except asyncio.CancelledError:
                raise
            except Exception:
                self._fingerprints.pop(job.process_id, None)
                _LOGGER.exception(
                    "Document build job failed",
                    extra={"processId": job.process_id},
                )
            finally:
                self._queue.task_done()
