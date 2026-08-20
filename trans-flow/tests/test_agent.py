from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from trans_flow.agent import OllamaTranslationAgent
from trans_flow.models import TranslationCommand


class RecordingClient:
    calls: list[dict[str, object]] = []

    def __init__(self, *, host: str) -> None:
        self.host = host

    async def chat(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(message=SimpleNamespace(content="<<<P0001-B001>>>\nПривет"))

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_ollama_translation_disables_reasoning(monkeypatch: pytest.MonkeyPatch) -> None:
    RecordingClient.calls.clear()
    monkeypatch.setitem(sys.modules, "ollama", SimpleNamespace(AsyncClient=RecordingClient))
    command = TranslationCommand.model_validate(
        {
            "processId": 1,
            "bookId": 1,
            "segmentId": 1,
            "requestId": "request-1",
            "stableKey": "P0001-B001",
            "sourceHash": "sha256:source",
            "sourceLanguage": "eng",
            "targetLanguage": "rus",
            "sourceText": "Hello",
            "marker": "<<<P0001-B001>>>",
            "glossary": [],
            "strategy": "single-v1",
            "previousIssues": [],
            "callbackPath": "/internal/v1/books/1/translations/1/fragments/1",
        }
    )

    agent = OllamaTranslationAgent(host="http://ollama:11434", model="qwen3:8b")
    await agent.translate(command)

    assert RecordingClient.calls[0]["think"] is False
