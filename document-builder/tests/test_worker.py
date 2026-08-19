from pathlib import Path

import pytest

from document_builder.input_validator import BuildInputValidator
from document_builder.models import BuildRequest
from document_builder.queue import BuildJob
from document_builder.settings import ServiceSettings
from document_builder.worker import BuildWorker


class RecordingCallback:
    def __init__(self) -> None:
        self.received_pdf = b""
        self.valid = False

    async def send(self, request, pdf_path: Path, report) -> None:
        self.received_pdf = pdf_path.read_bytes()
        self.valid = report.valid


@pytest.mark.asyncio
async def test_worker_renders_validates_callbacks_and_cleans_job(tmp_path: Path) -> None:
    settings = ServiceSettings(
        _env_file=None,
        build_temp_root=tmp_path,
        build_callback_retry_delay_seconds=0,
    )
    request = BuildRequest.model_validate(
        {
            "processId": 1,
            "bookId": 2,
            "resultCallbackUrl": "/internal/v1/books/2/build-result",
            "document": {"title": "Book", "language": "ru"},
            "elements": [
                {
                    "sequentialNumber": 1,
                    "type": "TEXT",
                    "text": "First control text",
                    "style": "HEADING_1",
                },
                {
                    "sequentialNumber": 2,
                    "type": "TEXT",
                    "text": "Last control text",
                    "style": "BODY",
                },
            ],
        }
    )
    snapshot = BuildInputValidator(settings).validate(request, ())
    callback = RecordingCallback()
    worker = BuildWorker(settings=settings, callback_client=callback)

    await worker(BuildJob(snapshot, snapshot.manifest_sha256))

    assert callback.received_pdf.startswith(b"%PDF-")
    assert callback.valid is True
    assert not snapshot.job_directory.exists()
