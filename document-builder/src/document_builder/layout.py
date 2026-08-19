from __future__ import annotations

from dataclasses import dataclass

from document_builder.models import BuildInput, ElementType
from document_builder.ordering import BlockKind, order_and_group


@dataclass(frozen=True, slots=True)
class LayoutElement:
    sequential_number: int
    type: str
    style: str | None
    text: str | None
    asset_uri: str | None
    alt_text: str | None


@dataclass(frozen=True, slots=True)
class LayoutBlock:
    kind: BlockKind
    elements: tuple[LayoutElement, ...]


@dataclass(frozen=True, slots=True)
class LayoutDocument:
    title: str
    language: str
    blocks: tuple[LayoutBlock, ...]


def create_layout(build_input: BuildInput) -> LayoutDocument:
    blocks: list[LayoutBlock] = []
    for block in order_and_group(build_input.elements):
        rendered: list[LayoutElement] = []
        for element in block.elements:
            asset_uri = None
            if element.type is ElementType.IMAGE and element.asset_key is not None:
                asset_uri = build_input.asset(element.asset_key).path.as_uri()
            rendered.append(
                LayoutElement(
                    sequential_number=element.sequential_number,
                    type=element.type.value,
                    style=element.style.value if element.style is not None else None,
                    text=element.text,
                    asset_uri=asset_uri,
                    alt_text=element.alt_text,
                )
            )
        blocks.append(LayoutBlock(kind=block.kind, elements=tuple(rendered)))
    return LayoutDocument(
        title=build_input.request.document.title,
        language=build_input.request.document.language,
        blocks=tuple(blocks),
    )
