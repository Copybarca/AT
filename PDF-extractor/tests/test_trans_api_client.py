
import json

import httpx
import pytest

from pdf_extractor.models import (
    BoundingBox,
    ElementStyle,
    ExtractedSegment,
    ExtractionCommand,
    ExtractionResult,
)
from pdf_extractor.trans_api_client import TransApiExtractionClient


def result() -> ExtractionResult:
    return ExtractionResult(
        command=ExtractionCommand(process_id=9, book_id=42, source_sha256=None),
        pdf_sha256="sha256:" + "a" * 64,
        algorithm_version="test-v1",
        segments=(
            ExtractedSegment(
                stable_key="P0001-B001-F001",
                source_hash="sha256:" + "b" * 64,
                sequential_number=1,
                physical_page=1,
                bbox=BoundingBox(x0=1, y0=2, x1=3, y1=4),
                style=ElementStyle.BODY,
                text="Source text.",
                translatable=True,
            ),
        ),
        images=(),
        regions=(),
    )


@pytest.mark.asyncio
async def test_client_publishes_complete_only_after_all_data_batches() -> None:
    paths: list[str] = []

    async def transport(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"accepted": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        client = TransApiExtractionClient(
            base_url="http://trans-api.local",
            service_token="secret",
            batch_size=100,
            http_client=http,
        )
        await client.publish(result())

    assert paths == [
        "/internal/v1/books/42/extraction/segments:batch",
        "/internal/v1/books/42/extraction/complete",
    ]


@pytest.mark.asyncio
async def test_client_never_sends_complete_after_failed_batch() -> None:
    paths: list[str] = []

    async def transport(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        client = TransApiExtractionClient(
            base_url="http://trans-api.local",
            service_token="secret",
            batch_size=100,
            http_client=http,
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.publish(result())

    assert paths == ["/internal/v1/books/42/extraction/segments:batch"]
    assert all(not path.endswith("/complete") for path in paths)


@pytest.mark.asyncio
async def test_client_reports_failed_extraction() -> None:
    requests: list[httpx.Request] = []

    async def transport(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        client = TransApiExtractionClient(
            base_url="http://trans-api.local",
            service_token="secret",
            batch_size=100,
            http_client=http,
        )
        await client.fail(result().command)

    [request] = requests
    assert request.url.path == "/internal/v1/books/42/extraction/failed"
    assert request.headers["Authorization"] == "Bearer secret"
    assert json.loads(request.content) == {"processId": 9}
