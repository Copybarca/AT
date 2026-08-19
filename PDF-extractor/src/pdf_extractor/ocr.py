from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from hashlib import sha256
from io import BytesIO
from typing import Any, Protocol

import pymupdf
import pytesseract  # type: ignore[import-untyped]
from PIL import Image, ImageOps

from pdf_extractor.models import (
    BoundingBox,
    ElementStyle,
    ImageTextRegion,
    RawTextBlock,
)


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

class ImageOcrEngine(Protocol):
    def extract_image(
        self,
        content: bytes,
        *,
        media_type: str,
        image_stable_key: str,
        physical_page: int,
    ) -> tuple[ImageTextRegion, ...]: ...


class TesseractImageOcrEngine:
    def __init__(
        self,
        *,
        language: str = "eng",
        minimum_confidence: float = 40,
    ) -> None:
        self._language = language
        self._minimum_confidence = minimum_confidence

    def extract_image(
        self,
        content: bytes,
        *,
        media_type: str,
        image_stable_key: str,
        physical_page: int,
    ) -> tuple[ImageTextRegion, ...]:
        del media_type
        original = Image.open(BytesIO(content)).convert("RGB")
        grayscale = ImageOps.autocontrast(ImageOps.grayscale(original))
        binary = grayscale.point(lambda value: 255 if value >= 160 else 0)
        variants = (original, grayscale, binary)
        candidates: list[RawTextBlock] = []
        for variant in variants:
            for page_segmentation_mode in (6, 11):
                data = pytesseract.image_to_data(
                    variant,
                    lang=self._language,
                    output_type=pytesseract.Output.DICT,
                    config=f"--psm {page_segmentation_mode}",
                )
                candidates.extend(
                    blocks_from_tesseract_data(
                        data,
                        physical_page=physical_page,
                        point_scale=1,
                        minimum_confidence=self._minimum_confidence,
                    )
                )

        unique: dict[tuple[str, int, int, int, int], RawTextBlock] = {}
        for candidate in candidates:
            key = (
                candidate.text.casefold(),
                round(candidate.bbox.x0),
                round(candidate.bbox.y0),
                round(candidate.bbox.x1),
                round(candidate.bbox.y1),
            )
            unique.setdefault(key, candidate)

        ordered = sorted(unique.values(), key=lambda item: (item.bbox.y0, item.bbox.x0))
        regions: list[ImageTextRegion] = []
        for region_number, candidate in enumerate(ordered, start=1):
            text_hash = sha256(candidate.text.encode("utf-8")).hexdigest()
            regions.append(
                ImageTextRegion(
                    image_stable_key=image_stable_key,
                    stable_key=f"{image_stable_key}-R{region_number:03d}",
                    source_hash=f"sha256:{text_hash}",
                    physical_page=physical_page,
                    sequential_number=region_number,
                    bbox=candidate.bbox,
                    text=candidate.text,
                    confidence=None,
                )
            )
        return tuple(regions)
