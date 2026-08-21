from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image

from pdf_extractor.extractor import PdfExtractionService
from pdf_extractor.figures import FigureExtractor, _opaque_png
from pdf_extractor.models import (
    BoundingBox,
    ElementStyle,
    ExtractionCommand,
    RawTextBlock,
)
from pdf_extractor.settings import FragmentationSettings
from pdf_extractor.text_layer import TextLayerExtractor


class DeterministicOcr:
    def __init__(self) -> None:
        self.called_pages: list[int] = []

    def extract_page(
        self,
        page: pymupdf.Page,
        physical_page: int,
    ) -> tuple[RawTextBlock, ...]:
        self.called_pages.append(physical_page)
        return (
            RawTextBlock(
                page_number=physical_page,
                block_number=1,
                stable_key=f"P{physical_page:04d}-B001",
                text="OCR fallback sentence.",
                bbox=BoundingBox(x0=10, y0=10, x1=200, y1=40),
                style=ElementStyle.BODY,
                translatable=True,
            ),
        )


def create_mixed_pdf(path: Path, image_path: Path) -> None:
    image = Image.new("RGB", (32, 20), color=(220, 10, 30))
    image.save(image_path, format="PNG")

    document = pymupdf.open()
    first = document.new_page()
    first.insert_text((72, 72), "Selectable sentence one. Sentence two.", fontsize=11)
    first.insert_image(pymupdf.Rect(72, 110, 168, 170), filename=str(image_path))
    document.new_page()
    document.save(path)
    document.close()


def test_extraction_service_uses_ocr_only_for_pages_without_text_layer(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "mixed.pdf"
    image_path = tmp_path / "figure.png"
    create_mixed_pdf(pdf_path, image_path)
    ocr = DeterministicOcr()
    service = PdfExtractionService(
        text_layer=TextLayerExtractor(),
        ocr_engine=ocr,
        figure_extractor=FigureExtractor(),
    )

    result = service.extract(
        pdf_path,
        ExtractionCommand(
            process_id=91,
            book_id=42,
            source_sha256=None,
        ),
        FragmentationSettings(
            min_sentences=1,
            max_sentences=3,
            boundary_tolerance_sentences=0,
        ),
    )

    assert ocr.called_pages == [2]
    assert [segment.text for segment in result.segments] == [
        "Selectable sentence one. Sentence two.",
        "OCR fallback sentence.",
    ]
    assert len(result.images) == 1
    assert result.images[0].media_type == "image/png"
    assert Image.open(BytesIO(result.images[0].content)).size == (32, 20)
    sequence = sorted(
        [segment.sequential_number for segment in result.segments]
        + [image.sequential_number for image in result.images]
    )
    assert sequence == [1, 2, 3]
    assert result.pdf_sha256.startswith("sha256:")
    assert result.expected_segment_count == 2
    assert result.expected_image_count == 1


def test_extraction_rejects_a_source_checksum_mismatch(tmp_path: Path) -> None:
    pdf_path = tmp_path / "book.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Enough selectable source text.")
    document.save(pdf_path)
    document.close()

    service = PdfExtractionService(
        text_layer=TextLayerExtractor(),
        ocr_engine=DeterministicOcr(),
        figure_extractor=FigureExtractor(),
    )

    try:
        service.extract(
            pdf_path,
            ExtractionCommand(
                process_id=1,
                book_id=2,
                source_sha256="sha256:" + "0" * 64,
            ),
            FragmentationSettings(),
        )
    except ValueError as error:
        assert str(error) == "Source PDF checksum does not match extraction command"
    else:
        raise AssertionError("Checksum mismatch must be rejected")


class DeterministicImageOcr:
    def extract_image(
        self,
        content: bytes,
        *,
        media_type: str,
        image_stable_key: str,
        physical_page: int,
    ):
        from pdf_extractor.models import ImageTextRegion

        assert content.startswith(b"\x89PNG")
        assert media_type == "image/png"
        return (
            ImageTextRegion(
                image_stable_key=image_stable_key,
                stable_key=f"{image_stable_key}-R001",
                source_hash="sha256:" + "c" * 64,
                physical_page=physical_page,
                sequential_number=1,
                bbox=BoundingBox(x0=1, y0=2, x1=20, y1=10),
                text="Diagram label",
                confidence=93.5,
            ),
        )


def test_figure_extractor_attaches_regions_from_injected_ocr(tmp_path: Path) -> None:
    pdf_path = tmp_path / "figure.pdf"
    image_path = tmp_path / "figure.png"
    image = Image.new("RGB", (32, 20), color=(220, 10, 30))
    image.save(image_path, format="PNG")
    document = pymupdf.open()
    page = document.new_page()
    page.insert_image(pymupdf.Rect(10, 20, 110, 80), filename=str(image_path))
    document.save(pdf_path)
    document.close()

    with pymupdf.open(pdf_path) as opened:
        [extracted] = FigureExtractor(
            image_ocr_engine=DeterministicImageOcr()
        ).extract_page(opened, opened[0], physical_page=1)

    assert [region.text for region in extracted.regions] == ["Diagram label"]
    assert extracted.regions[0].image_stable_key == extracted.stable_key
    assert extracted.regions[0].stable_key == "P0001-F001-R001"


def test_opaque_png_removes_alpha_channel() -> None:
    transparent = pymupdf.Pixmap(
        pymupdf.csRGB,
        pymupdf.IRect(0, 0, 2, 2),
        True,
    )
    transparent.clear_with(128)

    content = _opaque_png(transparent)

    with Image.open(BytesIO(content)) as image:
        assert image.format == "PNG"
        assert image.mode == "RGB"
