from __future__ import annotations

import asyncio

from document_builder.callback_client import BuildCallback
from document_builder.cleanup import remove_job_directory
from document_builder.html_renderer import HtmlRenderer
from document_builder.models import ElementType
from document_builder.pdf_renderer import PdfRenderer
from document_builder.pdf_validator import (
    PdfValidationExpectations,
    PdfValidator,
)
from document_builder.queue import BuildJob
from document_builder.settings import ServiceSettings


class PdfBuildError(RuntimeError):
    pass


class BuildWorker:
    def __init__(
        self,
        *,
        settings: ServiceSettings,
        callback_client: BuildCallback,
        html_renderer: HtmlRenderer | None = None,
        pdf_renderer: PdfRenderer | None = None,
        pdf_validator: PdfValidator | None = None,
    ) -> None:
        self._settings = settings
        self._callback = callback_client
        self._html = html_renderer or HtmlRenderer()
        self._pdf = pdf_renderer or PdfRenderer(settings)
        self._validator = pdf_validator or PdfValidator(settings)

    async def __call__(self, job: BuildJob) -> None:
        snapshot = job.build_input
        output = snapshot.job_directory / "result.pdf"
        try:
            async with asyncio.timeout(self._settings.build_timeout_seconds):
                html = self._html.render(snapshot)
                await asyncio.to_thread(
                    self._pdf.render,
                    html,
                    snapshot.job_directory,
                    output,
                )
                text_values = [
                    item.text
                    for item in snapshot.elements
                    if item.type is ElementType.TEXT and item.text is not None
                ]
                expected = PdfValidationExpectations(
                    first_control_text=text_values[0][:80],
                    last_control_text=text_values[-1][-80:],
                    expected_images=sum(
                        item.type is ElementType.IMAGE for item in snapshot.elements
                    ),
                )
                report = await asyncio.to_thread(
                    self._validator.validate,
                    output,
                    expected,
                )
                if not report.valid:
                    raise PdfBuildError("; ".join(report.issues))
                await self._callback.send(snapshot.request, output, report)
        finally:
            await asyncio.to_thread(remove_job_directory, snapshot.job_directory)
