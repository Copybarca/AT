from pdf_extractor.ocr import blocks_from_tesseract_data


def test_tesseract_words_are_grouped_into_ordered_text_lines() -> None:
    data = {
        "text": ["Hello", "world", "Second", "line"],
        "conf": ["94", "91", "88", "90"],
        "left": [10, 55, 10, 65],
        "top": [20, 20, 50, 50],
        "width": [40, 45, 50, 30],
        "height": [12, 12, 12, 12],
        "block_num": [1, 1, 1, 1],
        "par_num": [1, 1, 1, 1],
        "line_num": [1, 1, 2, 2],
    }

    blocks = blocks_from_tesseract_data(
        data,
        physical_page=3,
        point_scale=0.5,
        minimum_confidence=50,
    )

    assert [item.text for item in blocks] == ["Hello world", "Second line"]
    assert [item.stable_key for item in blocks] == [
        "P0003-B001",
        "P0003-B002",
    ]
    assert blocks[0].bbox.x0 == 5
    assert blocks[0].bbox.x1 == 50
