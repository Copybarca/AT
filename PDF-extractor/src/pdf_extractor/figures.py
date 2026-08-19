from __future__ import annotations

import pymupdf

from pdf_extractor.models import BoundingBox, ExtractedImage


class FigureExtractor:
    def extract_page(
        self,
        document: pymupdf.Document,
        page: pymupdf.Page,
        physical_page: int,
    ) -> tuple[ExtractedImage, ...]:
        images: list[ExtractedImage] = []
        seen_xrefs: set[int] = set()
        for figure_number, descriptor in enumerate(page.get_images(full=True), start=1):
            xref = int(descriptor[0])
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            extracted = document.extract_image(xref)
            extension = str(extracted.get("ext", "bin")).lower()
            media_type = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
            }.get(extension, f"image/{extension}")
            rectangles = page.get_image_rects(xref)
            rectangle = rectangles[0] if rectangles else pymupdf.Rect(0, 0, 0, 0)
            images.append(
                ExtractedImage(
                    stable_key=f"P{physical_page:04d}-F{figure_number:03d}",
                    sequential_number=0,
                    physical_page=physical_page,
                    bbox=BoundingBox(
                        x0=float(rectangle.x0),
                        y0=float(rectangle.y0),
                        x1=float(rectangle.x1),
                        y1=float(rectangle.y1),
                    ),
                    media_type=media_type,
                    content=bytes(extracted["image"]),
                    regions=(),
                )
            )
        return tuple(images)
