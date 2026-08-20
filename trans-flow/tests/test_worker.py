from __future__ import annotations

import pytest

from trans_flow.models import TranslationCallback, TranslationCommand, TranslationResultStatus
from trans_flow.queue import TranslationJob
from trans_flow.worker import (
    TranslationAgentError,
    TranslationRejectedError,
    TranslationWorker,
)


def command() -> TranslationCommand:
    return TranslationCommand.model_validate(
        {
            "processId": 11,
            "bookId": 42,
            "segmentId": 101,
            "requestId": "request-101",
            "stableKey": "P0001-B001",
            "sourceHash": "sha256:source",
            "sourceLanguage": "en",
            "targetLanguage": "ru",
            "sourceText": "Hello 2.0",
            "marker": "<<<P0001-B001>>>",
            "glossary": [],
            "strategy": "single-v1",
            "previousIssues": [],
            "callbackPath": "/internal/v1/books/42/translations/11/fragments/101",
        }
    )


class FakeAgent:
    model_name = "fake-model"

    def __init__(self, result: str | Exception) -> None:
        self.result = result

    async def translate(self, _: TranslationCommand) -> str:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    async def close(self) -> None:
        return None


class RecordingCallback:
    def __init__(self, accepted: bool = True) -> None:
        self.values: list[TranslationCallback] = []
        self.accepted = accepted

    async def send(
        self,
        _: TranslationCommand,
        callback: TranslationCallback,
    ) -> bool:
        self.values.append(callback)
        return self.accepted


@pytest.mark.asyncio
async def test_worker_sends_completed_callback() -> None:
    callback = RecordingCallback()
    worker = TranslationWorker(
        agent=FakeAgent("<<<P0001-B001>>>\nПривет 2.0"),
        callback_client=callback,  # type: ignore[arg-type]
        timeout_seconds=1,
    )

    await worker(TranslationJob(command=command(), fingerprint="same"))

    assert len(callback.values) == 1
    assert callback.values[0].status is TranslationResultStatus.COMPLETED
    assert callback.values[0].raw_response == "<<<P0001-B001>>>\nПривет 2.0"


@pytest.mark.asyncio
async def test_worker_reports_agent_failure() -> None:
    callback = RecordingCallback()
    worker = TranslationWorker(
        agent=FakeAgent(RuntimeError("model unavailable")),
        callback_client=callback,  # type: ignore[arg-type]
        timeout_seconds=1,
    )

    with pytest.raises(TranslationAgentError):
        await worker(TranslationJob(command=command(), fingerprint="same"))

    assert len(callback.values) == 1
    assert callback.values[0].status is TranslationResultStatus.FAILED
    assert callback.values[0].error == "RuntimeError: model unavailable"


@pytest.mark.asyncio
async def test_worker_releases_command_when_trans_api_rejects_candidate() -> None:
    callback = RecordingCallback(accepted=False)
    worker = TranslationWorker(
        agent=FakeAgent("<<<P0001-B001>>>\nПривет 2.0"),
        callback_client=callback,  # type: ignore[arg-type]
        timeout_seconds=1,
    )

    with pytest.raises(TranslationRejectedError):
        await worker(TranslationJob(command=command(), fingerprint="same"))
