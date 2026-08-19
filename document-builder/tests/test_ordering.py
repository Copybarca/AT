import pytest

from document_builder.models import BuildElement
from document_builder.ordering import BlockKind, OrderingError, order_and_group


def element(number: int, **values: object) -> BuildElement:
    data = {"sequentialNumber": number, **values}
    return BuildElement.model_validate(data)


def test_ordering_groups_heading_with_first_content_block() -> None:
    elements = (
        element(2, type="TEXT", text="Body", style="BODY"),
        element(1, type="TEXT", text="Heading", style="HEADING_1"),
    )

    blocks = order_and_group(elements)

    assert len(blocks) == 1
    assert blocks[0].kind is BlockKind.HEADING_WITH_CONTENT
    assert [item.text for item in blocks[0].elements] == ["Heading", "Body"]


def test_ordering_groups_image_with_immediately_following_caption() -> None:
    elements = (
        element(
            1,
            type="IMAGE",
            assetKey="figure-001",
            mediaType="image/png",
            altText="Figure",
        ),
        element(2, type="TEXT", text="Рисунок 1", style="FIGURE_CAPTION"),
        element(3, type="TEXT", text="Body", style="BODY"),
    )

    blocks = order_and_group(elements)

    assert blocks[0].kind is BlockKind.FIGURE_WITH_CAPTION
    assert [item.sequential_number for item in blocks[0].elements] == [1, 2]
    assert blocks[1].kind is BlockKind.TEXT


def test_ordering_combines_consecutive_list_items_and_preserves_code() -> None:
    source_code = "def answer():\n    return 42"
    elements = (
        element(1, type="TEXT", text="First", style="LIST_ITEM"),
        element(2, type="TEXT", text="Second", style="LIST_ITEM"),
        element(3, type="TEXT", text=source_code, style="CODE"),
    )

    blocks = order_and_group(elements)

    assert blocks[0].kind is BlockKind.LIST
    assert [item.text for item in blocks[0].elements] == ["First", "Second"]
    assert blocks[1].elements[0].text == source_code


def test_caption_without_preceding_image_is_rejected() -> None:
    caption = element(1, type="TEXT", text="Orphan", style="FIGURE_CAPTION")

    with pytest.raises(OrderingError, match="caption"):
        order_and_group((caption,))
