from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from pypdf import PdfReader

from document_builder.settings import ServiceSettings

_UNFINISHED_MARKERS = (
    "TRANSLATION PENDING",
    "{{",
    "}}",
)


@dataclass(frozen=True, slots=True)
class PdfValidationExpectations:
    first_control_text: str
    last_control_text: str
    expected_images: int


@dataclass(frozen=True, slots=True)
class PdfValidationReport:
    valid: bool
    page_count: int
    file_size: int
    sha256: str
    blank_pages: int
    image_instances: int
    issues: tuple[str, ...]


class PdfValidator:
    def __init__(self, settings: ServiceSettings) -> None:
        self._settings = settings

    def validate(
        self,
        path: Path,
        expected: PdfValidationExpectations,
    ) -> PdfValidationReport:
        issues: list[str] = []
        if not path.is_file() or path.stat().st_size == 0:
            return PdfValidationReport(
                valid=False,
                page_count=0,
                file_size=0,
                sha256="",
                blank_pages=0,
                image_instances=0,
                issues=("PDF file is missing or empty",),
            )

        content = path.read_bytes()
        digest = f"sha256:{sha256(content).hexdigest()}"
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            issues.append("PDF is unexpectedly encrypted")

        pages = tuple(reader.pages)
        if not pages:
            issues.append("PDF has no pages")

        expected_width = self._settings.page_width_in * 72
        expected_height = self._settings.page_height_in * 72
        extracted_pages: list[str] = []
        blank_pages = 0
        image_instances = 0
        for page_number, page in enumerate(pages, start=1):
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            if abs(width - expected_width) > 1 or abs(height - expected_height) > 1:
                issues.append(f"Page {page_number} has unexpected size")

            text = page.extract_text() or ""
            extracted_pages.append(text)
            page_images = len(page.images)
            image_instances += page_images
            if not text.strip() and page_images == 0:
                blank_pages += 1

        if blank_pages:
            issues.append(f"PDF has {blank_pages} unexpected blank pages")
        joined_text = _normalize_text("\n".join(extracted_pages))
        first_control_text = _normalize_text(expected.first_control_text)
        last_control_text = _normalize_text(expected.last_control_text)
        if first_control_text not in joined_text:
            issues.append("First control text is missing")
        if last_control_text not in joined_text:
            issues.append("Last control text is missing")
        for marker in _UNFINISHED_MARKERS:
            if marker in joined_text:
                issues.append(f"Unfinished marker remains: {marker}")
        if image_instances < expected.expected_images:
            issues.append(
                f"Expected at least {expected.expected_images} images, found {image_instances}"
            )

        return PdfValidationReport(
            valid=not issues,
            page_count=len(pages),
            file_size=len(content),
            sha256=digest,
            blank_pages=blank_pages,
            image_instances=image_instances,
            issues=tuple(issues),
        )


def _normalize_text(value: str) -> str:
    return " ".join(value.split())
