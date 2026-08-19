from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from weasyprint import HTML, URLFetcher  # type: ignore[import-untyped]

from document_builder.settings import ServiceSettings


class ExternalResourceError(ValueError):
    pass


def restricted_url_fetcher(
    url: str,
    asset_root: Path,
    fetcher: URLFetcher | None = None,
) -> Any:
    parsed = urlsplit(url)
    if parsed.scheme != "file":
        raise ExternalResourceError("Document may load only local job assets")
    requested = Path(unquote(parsed.path)).resolve()
    root = asset_root.resolve()
    if not requested.is_relative_to(root):
        raise ExternalResourceError("Document asset is outside the current job directory")
    active_fetcher = fetcher or URLFetcher(
        allowed_protocols=("file",),
        fail_on_errors=True,
    )
    return active_fetcher.fetch(url)


class PdfRenderer:
    def __init__(self, settings: ServiceSettings) -> None:
        self._settings = settings

    def render(self, html: str, asset_root: Path, output_path: Path) -> None:
        del self._settings
        fetcher = URLFetcher(allowed_protocols=("file",), fail_on_errors=True)
        try:
            document = HTML(
                string=html,
                base_url=asset_root.as_uri(),
                url_fetcher=lambda url: restricted_url_fetcher(
                    url,
                    asset_root,
                    fetcher,
                ),
            )
            document.write_pdf(output_path)
        finally:
            fetcher.close()
