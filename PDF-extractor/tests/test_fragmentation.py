from hashlib import sha256

from pdf_extractor.fragmentation import FragmentAssembler
from pdf_extractor.models import BoundingBox, ElementStyle, RawTextBlock
from pdf_extractor.settings import FragmentationSettings


def block(number: int, text: str) -> RawTextBlock:
    return RawTextBlock(
        page_number=1,
        block_number=number,
        stable_key=f"P0001-B{number:03d}",
        text=text,
        bbox=BoundingBox(x0=10, y0=20 * number, x1=500, y1=20 * number + 10),
        style=ElementStyle.BODY,
        translatable=True,
    )


def test_fragment_assembly_preserves_every_sentence_in_original_order() -> None:
    source = (
        block(1, "One. Two."),
        block(2, "Three. Four. Five."),
        block(3, "Six. Seven."),
    )
    settings = FragmentationSettings(
        min_sentences=2,
        max_sentences=3,
        boundary_tolerance_sentences=1,
    )

    fragments = FragmentAssembler().assemble(source, settings)

    reconstructed = " ".join(fragment.text for fragment in fragments)
    assert reconstructed == "One. Two. Three. Four. Five. Six. Seven."
    assert [fragment.sequential_number for fragment in fragments] == list(
        range(1, len(fragments) + 1)
    )
    assert len({fragment.stable_key for fragment in fragments}) == len(fragments)


def test_fragment_hash_is_sha256_of_normalized_fragment_text() -> None:
    source = (block(4, "First sentence.   Second sentence."),)
    settings = FragmentationSettings(
        min_sentences=1,
        max_sentences=5,
        boundary_tolerance_sentences=0,
    )

    [fragment] = FragmentAssembler().assemble(source, settings)

    assert fragment.text == "First sentence. Second sentence."
    expected = sha256(fragment.text.encode("utf-8")).hexdigest()
    assert fragment.source_hash == f"sha256:{expected}"
    assert fragment.stable_key == "P0001-B004-F001"


def test_non_translatable_code_block_remains_a_single_unchanged_element() -> None:
    code = RawTextBlock(
        page_number=2,
        block_number=3,
        stable_key="P0002-B003",
        text="def answer():\n    return 42",
        bbox=BoundingBox(x0=1, y0=2, x1=3, y1=4),
        style=ElementStyle.CODE,
        translatable=False,
    )
    settings = FragmentationSettings(
        min_sentences=5,
        max_sentences=10,
        boundary_tolerance_sentences=2,
    )

    [fragment] = FragmentAssembler().assemble((code,), settings)

    assert fragment.text == code.text
    assert fragment.style is ElementStyle.CODE
    assert fragment.translatable is False
