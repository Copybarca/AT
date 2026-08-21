from pathlib import Path

import pytest

from pdf_extractor.models import ExtractionCommand
from pdf_extractor.queue import ExtractionJob
from pdf_extractor.settings import FragmentationSettings
from pdf_extractor.worker import ExtractionWorker


class FailingExtractor:
    def extract(self, *_args):
        raise RuntimeError("broken image")


class RecordingClient:
    def __init__(self) -> None:
        self.failed: list[ExtractionCommand] = []

    async def publish(self, _result) -> None:
        raise AssertionError("A failed extraction must not be published")

    async def fail(self, command: ExtractionCommand) -> None:
        self.failed.append(command)


@pytest.mark.asyncio
async def test_worker_reports_failure_and_removes_temporary_files(tmp_path: Path) -> None:
    job_directory = tmp_path / "job"
    job_directory.mkdir()
    pdf_path = job_directory / "source.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n")
    command = ExtractionCommand(process_id=9, book_id=42)
    job = ExtractionJob(
        command=command,
        pdf_path=pdf_path,
        fragmentation=FragmentationSettings(),
        fingerprint="same",
        temp_directory=job_directory,
    )
    client = RecordingClient()

    with pytest.raises(RuntimeError, match="broken image"):
        await ExtractionWorker(FailingExtractor(), client)(job)

    assert client.failed == [command]
    assert not job_directory.exists()
