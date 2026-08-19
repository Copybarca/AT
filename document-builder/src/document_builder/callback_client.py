from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

import httpx

from document_builder.models import BuildRequest
from document_builder.pdf_validator import PdfValidationReport


class BuildCallback(Protocol):
    async def send(
        self,
        request: BuildRequest,
        pdf_path: Path,
        report: PdfValidationReport,
    ) -> None: ...


class BuildCallbackClient:
    def __init__(
        self,
        *,
        base_url: str,
        service_token: str,
        retries: int,
        retry_delay_seconds: float,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if retries < 1:
            raise ValueError("Callback retries must be positive")
        self._base_url = base_url.rstrip("/")
        self._token = service_token
        self._retries = retries
        self._delay = retry_delay_seconds
        self._http = http_client or httpx.AsyncClient(timeout=120)
        self._owns_client = http_client is None

    async def send(
        self,
        request: BuildRequest,
        pdf_path: Path,
        report: PdfValidationReport,
    ) -> None:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/pdf",
            "Content-Length": str(pdf_path.stat().st_size),
            "X-Process-Id": str(request.process_id),
            "X-Book-Id": str(request.book_id),
            "X-PDF-SHA256": report.sha256,
            "X-PDF-Page-Count": str(report.page_count),
        }
        for attempt in range(1, self._retries + 1):
            try:
                response = await self._http.post(
                    f"{self._base_url}{request.result_callback_url}",
                    headers=headers,
                    content=_file_chunks(pdf_path),
                )
                response.raise_for_status()
                return
            except (httpx.HTTPStatusError, httpx.RequestError):
                if attempt == self._retries:
                    raise
                await asyncio.sleep(self._delay)

    async def close(self) -> None:
        if self._owns_client:
            await self._http.aclose()


async def _file_chunks(path: Path) -> AsyncIterator[bytes]:
    with path.open("rb") as source:
        while chunk := await asyncio.to_thread(source.read, 1024 * 1024):
            yield chunk
