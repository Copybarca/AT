from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pymupdf

from pdf_extractor.figures import FigureExtractor
from pdf_extractor.fragmentation import FragmentAssembler
from pdf_extractor.models import (
    ExtractedImage,
    ExtractedSegment,
    ExtractionCommand,
    ExtractionResult,
)
from pdf_extractor.ocr import OcrEngine
from pdf_extractor.settings import FragmentationSettings
from pdf_extractor.text_layer import TextLayerExtractor


class PdfExtractionService:
    def __init__(
        self,
        *,
        text_layer: TextLayerExtractor,
        ocr_engine: OcrEngine,
        figure_extractor: FigureExtractor,
        fragment_assembler: FragmentAssembler | None = None,
        algorithm_version: str = "pdf-extractor-v1",
    ) -> None:
        self._text_layer = text_layer
        self._ocr = ocr_engine
        self._figures = figure_extractor
        self._fragments = fragment_assembler or FragmentAssembler()
        self._algorithm_version = algorithm_version

    def extract(
        self,
        pdf_path: Path,
        command: ExtractionCommand,
        fragmentation: FragmentationSettings,
    ) -> ExtractionResult:
        pdf_hash = _file_hash(pdf_path)
        if command.source_sha256 is not None and command.source_sha256 != pdf_hash:
            raise ValueError("Source PDF checksum does not match extraction command")

        segments: list[ExtractedSegment] = []
        images: list[ExtractedImage] = []
        with pymupdf.open(pdf_path) as document:
            if not document.is_pdf:
                raise ValueError("Extraction input must be a PDF document")
            for page_index, page in enumerate(document, start=1):
                layer = self._text_layer.extract_page(page, physical_page=page_index)
                blocks = (
                    layer.blocks
                    if layer.usable
                    else self._ocr.extract_page(page, physical_page=page_index)
                )
                segments.extend(self._fragments.assemble(blocks, fragmentation))
                images.extend(
                    self._figures.extract_page(document, page, physical_page=page_index)
                )

        ordered: list[tuple[int, float, float, str, int]] = []
        for index, segment in enumerate(segments):
            ordered.append(
                (
                    segment.physical_page,
                    segment.bbox.y0,
                    segment.bbox.x0,
                    "segment",
                    index,
                )
            )
        for index, image in enumerate(images):
            ordered.append(
                (
                    image.physical_page,
                    image.bbox.y0,
                    image.bbox.x0,
                    "image",
                    index,
                )
            )
        ordered.sort()

        next_sequence = 1
        for _, _, _, kind, index in ordered:
            if kind == "segment":
                segments[index] = replace(
                    segments[index],
                    sequential_number=next_sequence,
                )
            else:
                images[index] = replace(images[index], sequential_number=next_sequence)
            next_sequence += 1

        regions = tuple(region for image in images for region in image.regions)
        return ExtractionResult(
            command=command,
            pdf_sha256=pdf_hash,
            algorithm_version=self._algorithm_version,
            segments=tuple(segments),
            images=tuple(images),
            regions=regions,
        )


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"
