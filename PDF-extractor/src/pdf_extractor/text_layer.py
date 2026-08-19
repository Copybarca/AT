from __future__ import annotations

import re
from typing import Any

import pymupdf

from pdf_extractor.models import BoundingBox, ElementStyle, PageExtraction, RawTextBlock

_CODE_PATTERN = re.compile(
    r"(^|\n)\s*(def |class |import |from |return |if |for |while |\{|\}|//|#include)"
)


class TextLayerExtractor:
    def __init__(self, min_selectable_characters: int = 8) -> None:
        self._minimum = min_selectable_characters

    def extract_page(
        self,
        page: pymupdf.Page,
        physical_page: int,
    ) -> PageExtraction:
        page_dict: dict[str, Any] = page.get_text("dict")
        blocks: list[RawTextBlock] = []

        text_blocks = [
            block
            for block in page_dict.get("blocks", [])
            if block.get("type") == 0 and block.get("lines")
        ]
        text_blocks.sort(key=lambda block: (block["bbox"][1], block["bbox"][0]))

        for block_number, block in enumerate(text_blocks, start=1):
            lines: list[str] = []
            fonts: list[str] = []
            sizes: list[float] = []
            for line in block["lines"]:
                spans = line.get("spans", [])
                line_text = "".join(str(span.get("text", "")) for span in spans).rstrip()
                if line_text:
                    lines.append(line_text)
                fonts.extend(str(span.get("font", "")) for span in spans)
                sizes.extend(float(span.get("size", 0)) for span in spans)

            if not lines:
                continue
            text = "\n".join(lines)
            style = _classify_style(text, fonts, sizes)
            bbox = block["bbox"]
            blocks.append(
                RawTextBlock(
                    page_number=physical_page,
                    block_number=block_number,
                    stable_key=f"P{physical_page:04d}-B{block_number:03d}",
                    text=text,
                    bbox=BoundingBox(
                        x0=float(bbox[0]),
                        y0=float(bbox[1]),
                        x1=float(bbox[2]),
                        y1=float(bbox[3]),
                    ),
                    style=style,
                    translatable=style is not ElementStyle.CODE,
                )
            )

        selectable = sum(character.isalnum() for item in blocks for character in item.text)
        return PageExtraction(
            usable=selectable >= self._minimum,
            blocks=tuple(blocks),
        )


def _classify_style(
    text: str,
    fonts: list[str],
    sizes: list[float],
) -> ElementStyle:
    lowered_fonts = tuple(font.casefold() for font in fonts)
    if any("cour" in font or "mono" in font for font in lowered_fonts):
        return ElementStyle.CODE
    if _CODE_PATTERN.search(text):
        return ElementStyle.CODE

    maximum_size = max(sizes, default=0)
    if maximum_size >= 16:
        return ElementStyle.HEADING_1
    if maximum_size >= 13:
        return ElementStyle.HEADING_2
    if text.lstrip().startswith(("- ", "• ", "* ")):
        return ElementStyle.LIST_ITEM
    return ElementStyle.BODY
