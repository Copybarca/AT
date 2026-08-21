from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from pdf_extractor.extractor import PdfExtractionService
from pdf_extractor.queue import ExtractionJob
from pdf_extractor.trans_api_client import TransApiExtractionClient

_LOGGER = logging.getLogger(__name__)


class ExtractionWorker:
    def __init__(
        self,
        extractor: PdfExtractionService,
        client: TransApiExtractionClient,
    ) -> None:
        self._extractor = extractor
        self._client = client

    async def __call__(self, job: ExtractionJob) -> None:
        try:
            result = await asyncio.to_thread(
                self._extractor.extract,
                job.pdf_path,
                job.command,
                job.fragmentation,
            )
            await self._client.publish(result)
        except asyncio.CancelledError:
            raise
        except Exception:
            try:
                await self._client.fail(job.command)
            except Exception:
                _LOGGER.exception(
                    "Could not report extraction failure",
                    extra={"processId": job.command.process_id},
                )
            raise
        finally:
            await asyncio.to_thread(_remove_job_directory, job.temp_directory)


def _remove_job_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
