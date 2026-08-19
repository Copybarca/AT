from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pdf_extractor.models import ExtractionCommand
from pdf_extractor.settings import FragmentationSettings

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExtractionJob:
    command: ExtractionCommand
    pdf_path: Path
    fragmentation: FragmentationSettings
    fingerprint: str
    temp_directory: Path


class SubmitOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    FULL = "FULL"


JobHandler = Callable[[ExtractionJob], Awaitable[None]]


class ExtractionTaskQueue:
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
        self._queue: asyncio.Queue[ExtractionJob] = asyncio.Queue(maxsize=capacity)
        self._worker_count = worker_count
        self._handler = handler
        self._fingerprints: dict[int, str] = {}
        self._workers: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        if self._workers:
            return
        self._workers = [
            asyncio.create_task(self._run_worker(), name=f"extraction-worker-{index}")
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

    def submit(self, job: ExtractionJob) -> SubmitOutcome:
        existing = self._fingerprints.get(job.command.process_id)
        if existing is not None:
            return (
                SubmitOutcome.DUPLICATE
                if existing == job.fingerprint
                else SubmitOutcome.CONFLICT
            )
        if self._queue.full():
            return SubmitOutcome.FULL
        self._fingerprints[job.command.process_id] = job.fingerprint
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
                self._fingerprints.pop(job.command.process_id, None)
                _LOGGER.exception(
                    "Extraction job failed",
                    extra={"processId": job.command.process_id},
                )
            finally:
                self._queue.task_done()
