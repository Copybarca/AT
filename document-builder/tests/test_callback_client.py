from pathlib import Path

import httpx
import pytest

from document_builder.callback_client import BuildCallbackClient
from document_builder.models import BuildRequest
from document_builder.pdf_validator import PdfValidationReport


def request() -> BuildRequest:
    return BuildRequest.model_validate(
        {
            "processId": 9001,
            "bookId": 42,
            "resultCallbackUrl": "/internal/v1/books/42/build-result",
            "document": {"title": "Book", "language": "ru"},
            "elements": [
                {
                    "sequentialNumber": 1,
                    "type": "TEXT",
                    "text": "Body",
                    "style": "BODY",
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_callback_posts_raw_pdf_with_integrity_headers(tmp_path: Path) -> None:
    pdf = tmp_path / "result.pdf"
    body = b"%PDF-1.7\nvalidated"
    pdf.write_bytes(body)
    captured: list[tuple[httpx.Headers, bytes]] = []

    async def transport(incoming: httpx.Request) -> httpx.Response:
        captured.append((incoming.headers, await incoming.aread()))
        return httpx.Response(204)

    report = PdfValidationReport(
        valid=True,
        page_count=7,
        file_size=len(body),
        sha256="sha256:" + "a" * 64,
        blank_pages=0,
        image_instances=0,
        issues=(),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        client = BuildCallbackClient(
            base_url="http://trans-api.local",
            service_token="secret",
            retries=3,
            retry_delay_seconds=0,
            http_client=http,
        )
        await client.send(request(), pdf, report)

    assert len(captured) == 1
    headers, received = captured[0]
    assert received == body
    assert headers["content-type"] == "application/pdf"
    assert headers["x-process-id"] == "9001"
    assert headers["x-book-id"] == "42"
    assert headers["x-pdf-sha256"] == report.sha256
    assert headers["x-pdf-page-count"] == "7"
    assert headers["content-length"] == str(len(body))


@pytest.mark.asyncio
async def test_callback_retries_the_same_pdf_bytes(tmp_path: Path) -> None:
    pdf = tmp_path / "result.pdf"
    pdf.write_bytes(b"%PDF-1.7\nsame")
    bodies: list[bytes] = []

    async def transport(incoming: httpx.Request) -> httpx.Response:
        bodies.append(await incoming.aread())
        return httpx.Response(503 if len(bodies) == 1 else 200)

    report = PdfValidationReport(True, 1, pdf.stat().st_size, "sha256:x", 0, 0, ())
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        client = BuildCallbackClient(
            base_url="http://trans-api.local",
            service_token="secret",
            retries=2,
            retry_delay_seconds=0,
            http_client=http,
        )
        await client.send(request(), pdf, report)

    assert bodies == [pdf.read_bytes(), pdf.read_bytes()]
