from __future__ import annotations

import httpx
import pytest
from test_worker import command

from trans_flow.callback_client import TranslationCallbackClient
from trans_flow.models import TranslationCallback, TranslationResultStatus


@pytest.mark.asyncio
async def test_callback_uses_fixed_trans_api_origin_and_service_token() -> None:
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"accepted": True})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = TranslationCallbackClient(
        base_url="http://trans-api:8080",
        service_token="secret",
        retries=1,
        retry_delay_seconds=0,
        client=http,
    )
    value = TranslationCallback(
        requestId="request-101",
        sourceHash="sha256:source",
        status=TranslationResultStatus.COMPLETED,
        rawResponse="<<<P0001-B001>>>\nПеревод",
        model="fake",
        elapsedMilliseconds=10,
    )

    await client.send(command(), value)
    await http.aclose()

    assert len(captured) == 1
    assert str(captured[0].url) == (
        "http://trans-api:8080/internal/v1/books/42/translations/11/fragments/101"
    )
    assert captured[0].headers["authorization"] == "Bearer secret"
