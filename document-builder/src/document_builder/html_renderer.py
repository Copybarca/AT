from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from document_builder.layout import create_layout
from document_builder.models import BuildInput


class HtmlRenderer:
    def __init__(self, resource_root: Path | None = None) -> None:
        root = resource_root or Path(__file__).resolve().parent
        self._styles = (root / "styles" / "book.css").read_text(encoding="utf-8")
        self._environment = Environment(
            loader=FileSystemLoader(root / "templates"),
            autoescape=select_autoescape(default_for_string=True, default=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, build_input: BuildInput) -> str:
        template = self._environment.get_template("book.html")
        return template.render(
            document=create_layout(build_input),
            css=self._styles,
        )
