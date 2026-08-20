from __future__ import annotations

from fastapi.testclient import TestClient

from trans_flow.api import create_app
from trans_flow.queue import TranslationJob, TranslationTaskQueue
from trans_flow.settings import ServiceSettings


def payload(*, source_text: str = "Hello 2.0") -> dict[str, object]:
    return {
        "processId": 11,
        "bookId": 42,
        "segmentId": 101,
        "requestId": "request-101",
        "stableKey": "P0001-B001",
        "sourceHash": "sha256:source",
        "sourceLanguage": "en",
        "targetLanguage": "ru",
        "sourceText": source_text,
        "marker": "<<<P0001-B001>>>",
        "glossary": [],
        "strategy": "single-v1",
        "previousIssues": [],
        "callbackPath": "/internal/v1/books/42/translations/11/fragments/101",
    }


def test_accepts_one_fragment_and_deduplicates_replay() -> None:
    received: list[TranslationJob] = []

    async def handler(job: TranslationJob) -> None:
        received.append(job)

    queue = TranslationTaskQueue(capacity=2, worker_count=1, handler=handler)
    app = create_app(
        ServiceSettings(_env_file=None, service_token="secret"),
        queue=queue,
    )

    headers = {
        "Authorization": "Bearer secret",
        "Idempotency-Key": "translation-11-101",
    }
    with TestClient(app) as client:
        response = client.post("/internal/v1/translations", headers=headers, json=payload())
        replay = client.post("/internal/v1/translations", headers=headers, json=payload())

    assert response.status_code == 202
    assert response.json() == {
        "requestId": "request-101",
        "processId": 11,
        "segmentId": 101,
        "accepted": True,
    }
    assert replay.status_code == 202
    assert len(received) == 1


def test_rejects_unauthorized_invalid_key_and_absolute_callback() -> None:
    async def handler(_: TranslationJob) -> None:
        raise AssertionError("invalid command must not be queued")

    queue = TranslationTaskQueue(capacity=2, worker_count=1, handler=handler)
    app = create_app(
        ServiceSettings(_env_file=None, service_token="secret"),
        queue=queue,
    )

    with TestClient(app) as client:
        unauthorized = client.post("/internal/v1/translations", json=payload())
        wrong_key = client.post(
            "/internal/v1/translations",
            headers={
                "Authorization": "Bearer secret",
                "Idempotency-Key": "translation-11-999",
            },
            json=payload(),
        )
        bad_callback = payload()
        bad_callback["callbackPath"] = "http://attacker.invalid/callback"
        absolute_callback = client.post(
            "/internal/v1/translations",
            headers={
                "Authorization": "Bearer secret",
                "Idempotency-Key": "translation-11-101",
            },
            json=bad_callback,
        )

    assert unauthorized.status_code == 401
    assert wrong_key.status_code == 400
    assert absolute_callback.status_code == 422
