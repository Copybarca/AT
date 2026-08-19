from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256

from pdf_extractor.models import BoundingBox, ExtractedSegment, RawTextBlock
from pdf_extractor.settings import FragmentationSettings

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])(?:[\"'»”)]*)\s+")


@dataclass(frozen=True, slots=True)
class _Sentence:
    text: str
    block: RawTextBlock
    ends_block: bool


class FragmentAssembler:
    def assemble(
        self,
        blocks: Iterable[RawTextBlock],
        settings: FragmentationSettings,
    ) -> tuple[ExtractedSegment, ...]:
        output: list[ExtractedSegment] = []
        pending: list[_Sentence] = []
        fragment_numbers: defaultdict[str, int] = defaultdict(int)

        def emit_pending() -> None:
            nonlocal pending
            while pending:
                size = self._choose_size(pending, settings)
                selected = pending[:size]
                pending = pending[size:]
                first = selected[0].block
                fragment_numbers[first.stable_key] += 1
                text = " ".join(sentence.text for sentence in selected)
                output.append(
                    ExtractedSegment(
                        stable_key=(
                            f"{first.stable_key}-F"
                            f"{fragment_numbers[first.stable_key]:03d}"
                        ),
                        source_hash=_source_hash(text),
                        sequential_number=len(output) + 1,
                        physical_page=first.page_number,
                        bbox=_union_bbox(sentence.block.bbox for sentence in selected),
                        style=first.style,
                        text=text,
                        translatable=True,
                    )
                )

        for block in blocks:
            if not block.translatable:
                emit_pending()
                output.append(
                    ExtractedSegment(
                        stable_key=block.stable_key,
                        source_hash=_source_hash(block.text),
                        sequential_number=len(output) + 1,
                        physical_page=block.page_number,
                        bbox=block.bbox,
                        style=block.style,
                        text=block.text,
                        translatable=False,
                    )
                )
                continue

            sentences = _split_sentences(block.text)
            pending.extend(
                _Sentence(text=text, block=block, ends_block=index == len(sentences) - 1)
                for index, text in enumerate(sentences)
            )
            while len(pending) >= settings.max_sentences + settings.boundary_tolerance_sentences:
                size = self._choose_size(pending, settings)
                selected = pending[:size]
                pending = pending[size:]
                first = selected[0].block
                fragment_numbers[first.stable_key] += 1
                text = " ".join(sentence.text for sentence in selected)
                output.append(
                    ExtractedSegment(
                        stable_key=(
                            f"{first.stable_key}-F"
                            f"{fragment_numbers[first.stable_key]:03d}"
                        ),
                        source_hash=_source_hash(text),
                        sequential_number=len(output) + 1,
                        physical_page=first.page_number,
                        bbox=_union_bbox(sentence.block.bbox for sentence in selected),
                        style=first.style,
                        text=text,
                        translatable=True,
                    )
                )

        emit_pending()
        return tuple(output)

    @staticmethod
    def _choose_size(
        pending: list[_Sentence],
        settings: FragmentationSettings,
    ) -> int:
        if len(pending) <= settings.max_sentences:
            return len(pending)

        upper = min(
            len(pending),
            settings.max_sentences + settings.boundary_tolerance_sentences,
        )
        candidates = [
            index
            for index in range(settings.min_sentences, upper + 1)
            if pending[index - 1].ends_block
        ]
        if candidates:
            return min(
                candidates,
                key=lambda value: (abs(value - settings.max_sentences), value),
            )
        return min(settings.max_sentences, len(pending))


def _split_sentences(text: str) -> tuple[str, ...]:
    normalized = " ".join(text.split())
    if not normalized:
        return ()
    return tuple(part.strip() for part in _SENTENCE_BOUNDARY.split(normalized) if part.strip())


def _source_hash(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _union_bbox(boxes: Iterable[BoundingBox]) -> BoundingBox:
    materialized = tuple(boxes)
    return BoundingBox(
        x0=min(box.x0 for box in materialized),
        y0=min(box.y0 for box in materialized),
        x1=max(box.x1 for box in materialized),
        y1=max(box.y1 for box in materialized),
    )
