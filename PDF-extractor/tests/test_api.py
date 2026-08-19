import json
from pathlib import Path

from fastapi.testclient import TestClient

from pdf_extractor.api import create_app
from pdf_extractor.queue import ExtractionJob, ExtractionTaskQueue
from pdf_extractor.settings import (
    FragmentationSettings,
    RuntimeFragmentationSettings,
    ServiceSettings,
)


def settings(temp_root: Path) -> ServiceSettings:
    return ServiceSettings(
        _env_file=None,
        service_token="local-secret",
        extraction_temp_root=temp_root,
        extraction_queue_capacity=2,
        extraction_worker_count=1,
        max_request_bytes=1024 * 1024,
    )


def command(process_id: int = 10) -> str:
    return json.dumps(
        {
            "processId": process_id,
            "bookId": 42,
            "sourceSha256": None,
        }
    )


def test_extraction_api_accepts_valid_pdf_and_identical_replay(tmp_path: Path) -> None:
    received: list[ExtractionJob] = []

    async def handler(job: ExtractionJob) -> None:
        received.append(job)

    queue = ExtractionTaskQueue(capacity=2, worker_count=1, handler=handler)
    provider = RuntimeFragmentationSettings(FragmentationSettings())
    app = create_app(settings(tmp_path), queue=queue, fragmentation_provider=provider)

    with TestClient(app) as client:
        response = client.post(
            "/internal/v1/extractions",
            headers={
                "Authorization": "Bearer local-secret",
                "Idempotency-Key": "extraction-10",
            },
            data={"request": command()},
            files={"file": ("book.pdf", b"%PDF-1.7\nsynthetic", "application/pdf")},
        )
        replay = client.post(
            "/internal/v1/extractions",
            headers={
                "Authorization": "Bearer local-secret",
                "Idempotency-Key": "extraction-10",
            },
            data={"request": command()},
            files={"file": ("book.pdf", b"%PDF-1.7\nsynthetic", "application/pdf")},
        )

    assert response.status_code == 202
    assert response.json() == {"processId": 10, "accepted": True}
    assert replay.status_code == 202
    assert replay.json() == {"processId": 10, "accepted": True}
    assert len(received) == 1


def test_extraction_api_enforces_auth_idempotency_and_pdf_signature(
    tmp_path: Path,
) -> None:
    async def handler(_: ExtractionJob) -> None:
        raise AssertionError("invalid command must not be queued")

    queue = ExtractionTaskQueue(capacity=2, worker_count=1, handler=handler)
    app = create_app(settings(tmp_path), queue=queue)

    with TestClient(app) as client:
        unauthorized = client.post(
            "/internal/v1/extractions",
            data={"request": command()},
            files={"file": ("book.pdf", b"%PDF-1.7", "application/pdf")},
        )
        wrong_key = client.post(
            "/internal/v1/extractions",
            headers={
                "Authorization": "Bearer local-secret",
                "Idempotency-Key": "extraction-999",
            },
            data={"request": command()},
            files={"file": ("book.pdf", b"%PDF-1.7", "application/pdf")},
        )
        not_pdf = client.post(
            "/internal/v1/extractions",
            headers={
                "Authorization": "Bearer local-secret",
                "Idempotency-Key": "extraction-10",
            },
            data={"request": command()},
            files={"file": ("book.pdf", b"not a pdf", "application/pdf")},
        )

    assert unauthorized.status_code == 401
    assert wrong_key.status_code == 400
    assert not_pdf.status_code == 422


def test_fragmentation_settings_api_updates_only_future_snapshots(tmp_path: Path) -> None:
    queue = ExtractionTaskQueue(
        capacity=2,
        worker_count=1,
        handler=lambda _: _completed(),
    )
    provider = RuntimeFragmentationSettings(FragmentationSettings())
    app = create_app(settings(tmp_path), queue=queue, fragmentation_provider=provider)

    with TestClient(app) as client:
        updated = client.put(
            "/internal/v1/settings/fragmentation",
            headers={"Authorization": "Bearer local-secret"},
            json={
                "minSentences": 3,
                "maxSentences": 7,
                "boundaryToleranceSentences": 1,
            },
        )
        fetched = client.get(
            "/internal/v1/settings/fragmentation",
            headers={"Authorization": "Bearer local-secret"},
        )

    assert updated.status_code == 200
    assert fetched.json() == {
        "minSentences": 3,
        "maxSentences": 7,
        "boundaryToleranceSentences": 1,
    }


async def _completed() -> None:
    return None
