from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

import pymupdf
import pytesseract  # type: ignore[import-untyped]
from PIL import Image

from pdf_extractor.models import BoundingBox, ElementStyle, RawTextBlock


class OcrEngine(Protocol):
    def extract_page(
        self,
        page: pymupdf.Page,
        physical_page: int,
    ) -> tuple[RawTextBlock, ...]: ...


class TesseractOcrEngine:
    def __init__(
        self,
        dpi: int = 300,
        language: str = "eng",
        minimum_confidence: float = 40,
    ) -> None:
        self._dpi = dpi
        self._language = language
        self._minimum_confidence = minimum_confidence

    def extract_page(
        self,
        page: pymupdf.Page,
        physical_page: int,
    ) -> tuple[RawTextBlock, ...]:
        scale = self._dpi / 72
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        data = pytesseract.image_to_data(
            image,
            lang=self._language,
            output_type=pytesseract.Output.DICT,
            config="--psm 6",
        )
        return blocks_from_tesseract_data(
            data,
            physical_page=physical_page,
            point_scale=1 / scale,
            minimum_confidence=self._minimum_confidence,
        )


def blocks_from_tesseract_data(
    data: Mapping[str, Sequence[Any]],
    *,
    physical_page: int,
    point_scale: float,
    minimum_confidence: float,
) -> tuple[RawTextBlock, ...]:
    groups: defaultdict[tuple[int, int, int], list[int]] = defaultdict(list)
    for index, raw_text in enumerate(data.get("text", ())):
        text = str(raw_text).strip()
        try:
            confidence = float(data["conf"][index])
        except (KeyError, TypeError, ValueError):
            continue
        if text and confidence >= minimum_confidence:
            key = (
                int(data["block_num"][index]),
                int(data["par_num"][index]),
                int(data["line_num"][index]),
            )
            groups[key].append(index)

    blocks: list[RawTextBlock] = []
    ordered = sorted(
        groups.values(),
        key=lambda indices: (
            min(float(data["top"][index]) for index in indices),
            min(float(data["left"][index]) for index in indices),
        ),
    )
    for block_number, indices in enumerate(ordered, start=1):
        left = min(float(data["left"][index]) for index in indices)
        top = min(float(data["top"][index]) for index in indices)
        right = max(
            float(data["left"][index]) + float(data["width"][index])
            for index in indices
        )
        bottom = max(
            float(data["top"][index]) + float(data["height"][index])
            for index in indices
        )
        blocks.append(
            RawTextBlock(
                page_number=physical_page,
                block_number=block_number,
                stable_key=f"P{physical_page:04d}-B{block_number:03d}",
                text=" ".join(str(data["text"][index]).strip() for index in indices),
                bbox=BoundingBox(
                    x0=left * point_scale,
                    y0=top * point_scale,
                    x1=right * point_scale,
                    y1=bottom * point_scale,
                ),
                style=ElementStyle.BODY,
                translatable=True,
            )
        )
    return tuple(blocks)
