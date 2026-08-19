from io import BytesIO
from pathlib import Path

from PIL import Image

from document_builder.html_renderer import HtmlRenderer
from document_builder.input_validator import (
    BuildInputValidator,
    IncomingAsset,
)
from document_builder.models import BuildRequest
from document_builder.settings import ServiceSettings


def build_input(tmp_path: Path):
    image_buffer = BytesIO()
    Image.new("RGB", (40, 25), color=(10, 120, 30)).save(image_buffer, format="PNG")
    request = BuildRequest.model_validate(
        {
            "processId": 1,
            "bookId": 2,
            "resultCallbackUrl": "/internal/v1/books/2/build-result",
            "document": {"title": "Книга <безопасно>", "language": "ru"},
            "elements": [
                {
                    "sequentialNumber": 1,
                    "type": "TEXT",
                    "text": "Глава <script>alert(1)</script>",
                    "style": "HEADING_1",
                },
                {
                    "sequentialNumber": 2,
                    "type": "TEXT",
                    "text": "Первый абзац.",
                    "style": "BODY",
                },
                {
                    "sequentialNumber": 3,
                    "type": "TEXT",
                    "text": "Пункт один",
                    "style": "LIST_ITEM",
                },
                {
                    "sequentialNumber": 4,
                    "type": "TEXT",
                    "text": "Пункт два",
                    "style": "LIST_ITEM",
                },
                {
                    "sequentialNumber": 5,
                    "type": "IMAGE",
                    "assetKey": "figure-001",
                    "mediaType": "image/png",
                    "altText": "Figure",
                },
                {
                    "sequentialNumber": 6,
                    "type": "TEXT",
                    "text": "Рисунок 1",
                    "style": "FIGURE_CAPTION",
                },
                {
                    "sequentialNumber": 7,
                    "type": "TEXT",
                    "text": "def answer():\n    return 42",
                    "style": "CODE",
                },
            ],
        }
    )
    settings = ServiceSettings(_env_file=None, build_temp_root=tmp_path)
    return BuildInputValidator(settings).validate(
        request,
        (
            IncomingAsset(
                asset_key="figure-001",
                filename="figure.png",
                media_type="image/png",
                content=image_buffer.getvalue(),
            ),
        ),
    )


def test_html_renderer_escapes_text_and_preserves_structured_blocks(
    tmp_path: Path,
) -> None:
    snapshot = build_input(tmp_path)

    html = HtmlRenderer().render(snapshot)

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert html.count("<li>") == 2
    assert "def answer():\n    return 42" in html
    assert "<pre class=\"code\">" in html
    assert snapshot.assets[0].path.as_uri() in html
    assert "http://" not in html
    assert "https://" not in html
    assert "orphans: 3" in html
    assert "widows: 3" in html
    assert "break-inside: avoid-page" in html
