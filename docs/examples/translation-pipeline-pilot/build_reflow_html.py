#!/usr/bin/env python3
"""Build a clean, flowing Russian book layout from the keyed bilingual Markdown."""

from __future__ import annotations

import argparse
import html
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass
class Item:
    key: str
    page: int
    bbox: tuple[float, float, float, float]
    kind: str
    text: str = ""
    english: str = ""
    image: str = ""
    font_size: float = 10.0
    bold: bool = False
    italic: bool = False
    mono: bool = False


SECTION_RE = re.compile(
    r"^### (P(?P<page>\d{4})-(?P<kind>[BF])\d{3})\n(?P<body>.*?)"
    r"(?=^### P\d{4}-[BF]\d{3}\n|^<!-- BEGIN PDF PAGE|\Z)",
    re.M | re.S,
)


def parse_bbox(body: str) -> tuple[float, float, float, float]:
    match = re.search(r"bbox: \[([^]]+)\]", body)
    if not match:
        raise ValueError("section has no bbox")
    return tuple(float(part.strip()) for part in match.group(1).split(","))  # type: ignore[return-value]


def block_text(block: dict) -> str:
    return "\n".join(
        "".join(span["text"] for span in line["spans"])
        for line in block["lines"]
    ).strip()


def block_profile(block: dict) -> tuple[float, bool, bool, bool]:
    spans = [
        span
        for line in block["lines"]
        for span in line["spans"]
        if span["text"].strip()
    ]
    if not spans:
        return 10.0, False, False, False
    main = max(spans, key=lambda span: len(span["text"]))
    name = main["font"].lower()
    mono = any(marker in name for marker in ("mono", "courier", "ubuntu", "code"))
    bold = any(marker in name for marker in ("bold", "semibold", "demi"))
    italic = any(marker in name for marker in ("italic", "oblique", "-it"))
    return float(main["size"]), bold, italic, mono


def match_block(page: fitz.Page, bbox: tuple[float, float, float, float]) -> dict | None:
    rect = fitz.Rect(bbox)
    candidates = []
    for block in page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]:
        if block["type"] != 0 or not block_text(block):
            continue
        overlap = (rect & fitz.Rect(block["bbox"])).get_area() / max(1.0, rect.get_area())
        candidates.append((overlap, block))
    if not candidates:
        return None
    overlap, block = max(candidates, key=lambda pair: pair[0])
    return block if overlap >= 0.9 else None


def parse_items(markdown: Path, source_pdf: Path, end_page: int) -> list[Item]:
    source = fitz.open(source_pdf)
    raw = markdown.read_text(encoding="utf-8")
    items: list[Item] = []
    segment_rects: dict[int, list[fitz.Rect]] = {page: [] for page in range(1, end_page + 1)}

    for match in SECTION_RE.finditer(raw):
        page_number = int(match.group("page"))
        if page_number > end_page:
            continue
        body = match.group("body")
        bbox = parse_bbox(body)
        if match.group("kind") == "F":
            image_match = re.search(r"!\[[^]]*\]\(([^)]+)\)", body)
            if image_match:
                items.append(Item(match.group(1), page_number, bbox, "figure", image=image_match.group(1)))
            continue

        english_match = re.search(r"^English:\s*\n(.*?)(?=^Russian:\s*$)", body, re.M | re.S)
        russian_match = re.search(r"^Russian:\s*\n(.*)\Z", body, re.M | re.S)
        if not english_match or not russian_match:
            raise ValueError(f"cannot parse {match.group(1)}")
        russian = russian_match.group(1).strip()
        if not russian or "TRANSLATION PENDING" in russian:
            raise ValueError(f"untranslated segment {match.group(1)}")
        english = english_match.group(1).strip()
        block = match_block(source[page_number - 1], bbox)
        profile = block_profile(block) if block else (10.0, False, False, False)
        items.append(
            Item(
                match.group(1), page_number, bbox, "text", russian, english,
                font_size=profile[0], bold=profile[1], italic=profile[2], mono=profile[3],
            )
        )
        segment_rects[page_number].append(fitz.Rect(bbox))

    # Code was intentionally excluded from translation memory. Reinsert exact source code
    # as flowing preformatted blocks, but ignore barcodes, isolated page numbers, and artwork text.
    for page_number in range(1, end_page + 1):
        page = source[page_number - 1]
        for index, block in enumerate(page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]):
            if block["type"] != 0:
                continue
            text = block_text(block)
            if len(text) < 10:
                continue
            rect = fitz.Rect(block["bbox"])
            if rect.y0 > 600:
                continue
            coverage = max(
                ((rect & keyed).get_area() / max(1.0, rect.get_area()) for keyed in segment_rects[page_number]),
                default=0.0,
            )
            size, bold, italic, mono = block_profile(block)
            if coverage < 0.3 and mono:
                items.append(
                    Item(
                        f"P{page_number:04d}-C{index:03d}", page_number,
                        tuple(block["bbox"]), "code", text=text, font_size=size,
                        bold=bold, italic=italic, mono=True,
                    )
                )

    back_cover_order = {
        "P0002-B015": 10, "P0002-B016": 11, "P0002-B017": 12,
        "P0002-B014": 20, "P0002-B007": 30, "P0002-B008": 31,
        "P0002-B009": 40, "P0002-B010": 41, "P0002-B011": 42,
        "P0002-B012": 43, "P0002-B013": 44, "P0002-B004": 50,
        "P0002-B005": 51, "P0002-B006": 52, "P0002-B003": 60,
        "P0002-B002": 61,
    }
    items.sort(
        key=lambda item: (
            item.page,
            back_cover_order.get(item.key, 1000 + int(item.bbox[1] * 10)) if item.page == 2 else item.bbox[1],
            item.bbox[0],
            item.key,
        )
    )
    return items


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def classify(item: Item) -> str:
    text = normalize(item.text)
    english = normalize(item.english)
    if item.kind != "text":
        return item.kind
    if item.bbox[1] > 600:
        return "running-footer"
    if item.page in range(7, 15):
        if item.font_size >= 16 or english.lower() in {"contents", "table of contents"}:
            return "h1"
        return "toc"
    if re.match(r"^(CHAPTER|ГЛАВА)\b", english, re.I) or re.match(r"^ГЛАВА\b", text, re.I):
        return "chapter"
    if re.match(r"^(PART|Часть)\b", english, re.I) and item.font_size >= 12:
        return "part"
    if re.match(r"^(Figure|Рисунок|Example|Пример)\b", text, re.I):
        return "caption"
    if item.mono:
        return "code"
    if item.font_size >= 17:
        return "h1"
    if item.font_size >= 13 or (item.bold and len(text) < 140):
        return "h2"
    if (item.font_size >= 10.5 and item.bold and len(text) < 180):
        return "h3"
    if text.startswith("•"):
        return "list"
    if item.font_size <= 8.5 and item.bbox[0] > 80:
        return "note"
    return "body"


def file_uri(asset_root: str, relative: str) -> str:
    source = Path(relative)
    if source.is_absolute():
        try:
            relative = source.relative_to(Path(__file__).resolve().parent).as_posix()
        except ValueError as exc:
            raise ValueError(f"image is outside the project: {source}") from exc
    path = f"{asset_root.rstrip('/')}/{relative.lstrip('/')}"
    return "file://" + urllib.parse.quote(path, safe="/")


def render_text(text: str) -> str:
    return html.escape(normalize(text), quote=True)


def render_html(items: list[Item], asset_root: str, show_keys: bool = False) -> str:
    body: list[str] = []
    list_buffer: list[tuple[str, str]] = []
    toc_buffer: list[tuple[str, str]] = []

    def review_key(key: str) -> str:
        if not show_keys:
            return ""
        return f'<span class="review-key">{html.escape(key)}</span>'

    def flush_list() -> None:
        if not list_buffer:
            return
        body.append('<ul class="book-list">')
        for key, value in list_buffer:
            body.append(f"<li>{review_key(key)}{render_text(value)}</li>")
        body.append("</ul>")
        list_buffer.clear()

    def flush_toc() -> None:
        if not toc_buffer:
            return
        body.append('<div class="toc-block">')
        for key, line in toc_buffer:
            body.append(
                f'<span class="toc-line">{review_key(key)}{html.escape(line)}</span><br>'
            )
        body.append('</div>')
        toc_buffer.clear()

    # The exported translation split the back-cover list across physical blocks.
    back_list_keys = {f"P0002-B{index:03d}" for index in range(9, 14)}
    back_list_text = " ".join(item.text for item in items if item.key in back_list_keys)
    back_list_done = False

    previous_body: Item | None = None
    previous_page = 0
    for item in items:
        if item.page == 2 and previous_page == 1:
            flush_list()
            body.append('<div class="page-break"></div>')
            previous_body = None
        previous_page = item.page
        if item.key in back_list_keys:
            if back_list_done:
                continue
            back_list_done = True
            chunks = [normalize(chunk) for chunk in re.split(r"\s*•\s*", back_list_text) if normalize(chunk)]
            list_buffer.extend((item.key, chunk) for chunk in chunks)
            continue

        kind = classify(item)
        if kind != "list":
            flush_list()
        if kind != "toc":
            flush_toc()
        if kind == "running-footer":
            continue
        if item.key == "P0015-B000":
            body.append('<div class="page-break"></div>')
        if item.key == "P0001-B001":
            body.append(
                f'<h1 class="cover-title">{review_key(item.key)}'
                f'{html.escape(normalize(item.text))}</h1>'
            )
            previous_body = None
            continue
        if item.key == "P0001-B002":
            body.append(
                f'<p class="cover-subtitle">{review_key(item.key)}'
                f'{html.escape(normalize(item.text))}</p>'
            )
            previous_body = None
            continue
        if item.key == "P0001-B000":
            body.append(
                f'<p class="cover-authors">{review_key(item.key)}'
                f'{html.escape(normalize(item.text))}</p>'
            )
            previous_body = None
            continue
        if kind == "figure":
            width = max(18.0, min(100.0, (item.bbox[2] - item.bbox[0]) / 3.6))
            css = "cover-art" if item.key == "P0001-F001" else "book-figure"
            body.append(
                f'<figure class="{css}">{review_key(item.key)}'
                f'<img src="{html.escape(file_uri(asset_root, item.image), quote=True)}" '
                f'style="width:{width:.1f}%" alt="{html.escape(item.key)}"></figure>'
            )
            previous_body = None
            continue
        if kind == "code":
            body.append(
                f'{review_key(item.key)}<pre class="code">'
                f'{html.escape(item.text.rstrip())}</pre>'
            )
            previous_body = None
            continue
        if kind == "list":
            chunks = [normalize(chunk) for chunk in re.split(r"\s*•\s*", item.text) if normalize(chunk)]
            list_buffer.extend((item.key, chunk) for chunk in chunks)
            previous_body = None
            continue
        if kind == "toc":
            lines = [normalize(line) for line in item.text.splitlines() if normalize(line)]
            toc_buffer.extend((item.key, line) for line in lines)
            previous_body = None
            continue

        text = normalize(item.text)
        class_name = kind
        tag = {
            "chapter": "h1", "part": "h1", "h1": "h1", "h2": "h2", "h3": "h3",
            "caption": "figcaption", "note": "aside", "body": "p",
        }.get(kind, "p")
        # Join paragraphs that were split only by an original physical page boundary.
        if (
            kind == "body" and previous_body is not None and previous_body.page + 1 == item.page
            and item.english[:1].islower() and body and body[-1].startswith('<p class="body">')
        ):
            prior = body.pop()
            prior_text = re.sub(r"^<p class=\"body\">|</p>$", "", prior)
            body.append(
                f'<p class="body">{prior_text} {review_key(item.key)}'
                f'{html.escape(text)}</p>'
            )
        else:
            body.append(
                f'<{tag} class="{class_name}">{review_key(item.key)}'
                f'{html.escape(text)}</{tag}>'
            )
        previous_body = item if kind == "body" else None

    flush_list()
    flush_toc()
    content = "\n".join(body)
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Безопасность данных в облачно-нативных системах с OAuth</title>
<style>
@page {{ size: 7in 9.1875in; margin: 0.68in 0.72in 0.72in; }}
* {{ box-sizing: border-box; }}
html {{ font-family: "Noto Serif", serif; color: #171717; font-size: 10.5pt; line-height: 1.47; }}
body {{ margin: 0; padding: 0; font-variant-numeric: lining-nums tabular-nums; }}
p {{ margin: 0 0 0.8em; text-align: left; orphans: 3; widows: 3; hyphens: auto; }}
h1, h2, h3 {{
  font-family: "Noto Serif", serif;
  line-height: 1.18;
  break-inside: avoid-page;
  page-break-inside: avoid;
  break-after: avoid-page;
  page-break-after: avoid;
  color: #101010;
}}
h1 + p, h1 + ul, h1 + pre, h2 + p, h2 + ul, h2 + pre, h3 + p, h3 + ul, h3 + pre {{
  break-before: avoid-page;
  page-break-before: avoid;
}}
h1 {{ font-size: 22pt; margin: 1.2em 0 0.55em; }}
h2 {{ font-size: 15pt; margin: 1.15em 0 0.45em; }}
h3 {{ font-size: 11.5pt; margin: 1em 0 0.35em; }}
.chapter, .part {{ break-before: page; page-break-before: always; font-size: 24pt; margin-top: 0; padding-top: 1.25in; }}
.caption {{ font-size: 9pt; line-height: 1.35; font-style: italic; margin: -0.25em 0 1.1em; break-after: avoid; }}
.note {{ display: block; font-size: 8.5pt; line-height: 1.35; margin: 0.35em 1.5em 0.8em; }}
.book-list {{ margin: 0.2em 0 1em 1.25em; padding: 0; }}
.book-list li {{ padding-left: 0.3em; margin: 0 0 0.4em; break-inside: avoid; }}
.code {{ font-family: "IBM Plex Mono", monospace; font-size: 7.6pt; line-height: 1.35; white-space: pre-wrap; overflow-wrap: anywhere; background: #f4f5f6; border-left: 3px solid #cf181f; padding: 0.75em 0.9em; margin: 0.45em 0 1em; break-inside: avoid; }}
.book-figure, .cover-art {{ margin: 1em 0 0.8em; text-align: center; break-inside: avoid; }}
.book-figure img, .cover-art img {{ height: auto; max-height: 6.5in; object-fit: contain; }}
.cover-art img {{ max-height: 5.1in; }}
.cover-title {{ font-size: 28pt; line-height: 1.12; margin: 0 0 0.35em; break-inside: avoid-page; page-break-inside: avoid; }}
.cover-subtitle {{ font-size: 14pt; line-height: 1.3; color: #4f6787; margin: 0 0 0.8em; }}
.cover-authors {{ font-size: 12pt; line-height: 1.35; margin: 0.4em 0 0; }}
.toc-block {{ margin: 0.25em 0 0.9em; font-size: 9.7pt; line-height: 1.33; orphans: 4; widows: 4; }}
.toc-line {{ padding: 0.1em 0; }}
.review-key {{
  display: inline-block;
  vertical-align: 0.12em;
  margin: 0 0.45em 0.12em 0;
  padding: 0.08em 0.3em;
  border: 0.5px solid #9b9b9b;
  border-radius: 2px;
  color: #666;
  font-family: "IBM Plex Mono", monospace;
  font-size: 6.3pt;
  font-weight: normal;
  font-style: normal;
  line-height: 1.15;
}}
.page-break {{ break-before: page; page-break-before: always; height: 0; }}
body > :first-child {{ margin-top: 0; }}
@media print {{ a {{ color: inherit; text-decoration: none; }} }}
</style>
</head>
<body>
{content}
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--asset-root", required=True)
    parser.add_argument("--end-page", type=int, default=60)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--show-keys", action="store_true", help="show segment and figure keys for review"
    )
    args = parser.parse_args()
    items = parse_items(args.markdown, args.source_pdf, args.end_page)
    args.output.write_text(
        render_html(items, args.asset_root, show_keys=args.show_keys), encoding="utf-8"
    )
    print(f"wrote {args.output}: {len(items)} ordered items")


if __name__ == "__main__":
    main()
