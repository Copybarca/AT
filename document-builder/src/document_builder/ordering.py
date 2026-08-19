from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from document_builder.models import BuildElement, ElementType, TextStyle


class OrderingError(ValueError):
    pass


class BlockKind(StrEnum):
    TEXT = "TEXT"
    HEADING_WITH_CONTENT = "HEADING_WITH_CONTENT"
    FIGURE = "FIGURE"
    FIGURE_WITH_CAPTION = "FIGURE_WITH_CAPTION"
    LIST = "LIST"
    CODE = "CODE"
    NOTE = "NOTE"


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    kind: BlockKind
    elements: tuple[BuildElement, ...]


_HEADING_STYLES = {
    TextStyle.TITLE,
    TextStyle.CHAPTER,
    TextStyle.HEADING_1,
    TextStyle.HEADING_2,
    TextStyle.HEADING_3,
}


def order_and_group(elements: tuple[BuildElement, ...]) -> tuple[DocumentBlock, ...]:
    ordered = tuple(sorted(elements, key=lambda item: item.sequential_number))
    if [item.sequential_number for item in ordered] != list(range(1, len(ordered) + 1)):
        raise OrderingError("Element sequence must be continuous")

    blocks: list[DocumentBlock] = []
    index = 0
    while index < len(ordered):
        current = ordered[index]
        if current.style is TextStyle.FIGURE_CAPTION:
            raise OrderingError("Figure caption must immediately follow an image")

        if current.type is ElementType.IMAGE:
            if (
                index + 1 < len(ordered)
                and ordered[index + 1].style is TextStyle.FIGURE_CAPTION
            ):
                blocks.append(
                    DocumentBlock(
                        kind=BlockKind.FIGURE_WITH_CAPTION,
                        elements=(current, ordered[index + 1]),
                    )
                )
                index += 2
            else:
                blocks.append(DocumentBlock(kind=BlockKind.FIGURE, elements=(current,)))
                index += 1
            continue

        if current.style in _HEADING_STYLES and index + 1 < len(ordered):
            following = ordered[index + 1]
            grouped = [current, following]
            if (
                following.type is ElementType.IMAGE
                and index + 2 < len(ordered)
                and ordered[index + 2].style is TextStyle.FIGURE_CAPTION
            ):
                grouped.append(ordered[index + 2])
            blocks.append(
                DocumentBlock(
                    kind=BlockKind.HEADING_WITH_CONTENT,
                    elements=tuple(grouped),
                )
            )
            index += len(grouped)
            continue

        if current.style is TextStyle.LIST_ITEM:
            grouped = [current]
            index += 1
            while index < len(ordered) and ordered[index].style is TextStyle.LIST_ITEM:
                grouped.append(ordered[index])
                index += 1
            blocks.append(DocumentBlock(kind=BlockKind.LIST, elements=tuple(grouped)))
            continue

        if current.style is TextStyle.CODE:
            kind = BlockKind.CODE
        elif current.style is TextStyle.NOTE:
            kind = BlockKind.NOTE
        else:
            kind = BlockKind.TEXT
        blocks.append(DocumentBlock(kind=kind, elements=(current,)))
        index += 1

    return tuple(blocks)
