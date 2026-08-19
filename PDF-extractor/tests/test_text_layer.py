from pathlib import Path

import pymupdf

from pdf_extractor.models import ElementStyle
from pdf_extractor.text_layer import TextLayerExtractor


def create_text_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Chapter title", fontsize=18, fontname="helv")
    page.insert_text((72, 110), "First body paragraph.", fontsize=11, fontname="helv")
    page.insert_text((72, 145), "def answer():", fontsize=10, fontname="cour")
    page.insert_text((72, 160), "    return 42", fontsize=10, fontname="cour")
    document.save(path)
    document.close()


def test_text_layer_returns_ordered_blocks_with_bbox_and_styles(tmp_path: Path) -> None:
    pdf_path = tmp_path / "text.pdf"
    create_text_pdf(pdf_path)

    with pymupdf.open(pdf_path) as document:
        result = TextLayerExtractor().extract_page(document[0], physical_page=1)

    assert result.usable is True
    assert [block.text for block in result.blocks] == [
        "Chapter title",
        "First body paragraph.",
        "def answer():\n    return 42",
    ]
    assert result.blocks[0].style is ElementStyle.HEADING_1
    assert result.blocks[1].style is ElementStyle.BODY
    assert result.blocks[2].style is ElementStyle.CODE
    assert result.blocks[2].translatable is False
    assert result.blocks[0].stable_key == "P0001-B001"
    assert result.blocks[0].bbox.y0 < result.blocks[1].bbox.y0


def test_blank_page_is_not_considered_a_usable_text_layer() -> None:
    document = pymupdf.open()
    page = document.new_page()

    result = TextLayerExtractor(min_selectable_characters=8).extract_page(
        page,
        physical_page=1,
    )

    assert result.usable is False
    assert result.blocks == ()
    document.close()
