from pathlib import Path

import pytest
from test_html_renderer import build_input

from document_builder.html_renderer import HtmlRenderer
from document_builder.pdf_renderer import (
    ExternalResourceError,
    PdfRenderer,
    restricted_url_fetcher,
)
from document_builder.pdf_validator import (
    PdfValidationExpectations,
    PdfValidator,
)
from document_builder.settings import ServiceSettings


def test_renderer_blocks_external_resources(tmp_path: Path) -> None:
    with pytest.raises(ExternalResourceError):
        restricted_url_fetcher("https://example.com/tracker.png", tmp_path)


def test_weasyprint_output_passes_independent_pdf_validation(tmp_path: Path) -> None:
    snapshot = build_input(tmp_path)
    settings = ServiceSettings(_env_file=None, build_temp_root=tmp_path)
    html = HtmlRenderer().render(snapshot)
    output = snapshot.job_directory / "result.pdf"

    PdfRenderer(settings).render(html, snapshot.job_directory, output)
    report = PdfValidator(settings).validate(
        output,
        PdfValidationExpectations(
            first_control_text="Глава",
            last_control_text="return 42",
            expected_images=1,
        ),
    )

    assert report.valid is True
    assert report.page_count > 0
    assert report.file_size > 0
    assert report.sha256.startswith("sha256:")
    assert report.blank_pages == 0
    assert report.image_instances >= 1
    assert report.issues == ()
