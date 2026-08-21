from __future__ import annotations

import json
from collections.abc import Iterable

import httpx

from pdf_extractor.models import (
    BoundingBox,
    ExtractedSegment,
    ExtractionCommand,
    ExtractionResult,
    ImageTextRegion,
)


class TransApiExtractionClient:
    def __init__(
        self,
        *,
        base_url: str,
        service_token: str,
        batch_size: int,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError("Batch size must be positive")
        self._base_url = base_url.rstrip("/")
        self._token = service_token
        self._batch_size = batch_size
        self._http = http_client or httpx.AsyncClient(timeout=60)
        self._owns_client = http_client is None

    async def publish(self, result: ExtractionResult) -> None:
        book_id = result.command.book_id
        process_id = result.command.process_id
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Idempotency-Key": f"extraction-{process_id}",
        }

        for segment_batch in _batches(result.segments, self._batch_size):
            response = await self._http.post(
                f"{self._base_url}/internal/v1/books/{book_id}"
                "/extraction/segments:batch",
                headers=headers,
                json={
                    "processId": process_id,
                    "segments": [_segment_payload(segment) for segment in segment_batch],
                },
            )
            response.raise_for_status()

        for image in result.images:
            metadata = {
                "processId": process_id,
                "stableKey": image.stable_key,
                "sequentialNumber": image.sequential_number,
                "physicalPage": image.physical_page,
                "bbox": _bbox_payload(image.bbox),
                "mediaType": image.media_type,
            }
            response = await self._http.post(
                f"{self._base_url}/internal/v1/books/{book_id}/extraction/images",
                headers=headers,
                files={
                    "request": (
                        None,
                        json.dumps(metadata, separators=(",", ":")),
                        "application/json",
                    ),
                    "file": (
                        f"{image.stable_key}.{_extension(image.media_type)}",
                        image.content,
                        image.media_type,
                    ),
                },
            )
            response.raise_for_status()

        for region_batch in _batches(result.regions, self._batch_size):
            response = await self._http.post(
                f"{self._base_url}/internal/v1/books/{book_id}"
                "/extraction/image-regions:batch",
                headers=headers,
                json={
                    "processId": process_id,
                    "regions": [_region_payload(region) for region in region_batch],
                },
            )
            response.raise_for_status()

        response = await self._http.post(
            f"{self._base_url}/internal/v1/books/{book_id}/extraction/complete",
            headers=headers,
            json={
                "processId": process_id,
                "pdfSha256": result.pdf_sha256,
                "extractorVersion": result.algorithm_version,
                "expectedSegmentCount": result.expected_segment_count,
                "expectedImageCount": result.expected_image_count,
                "expectedRegionCount": result.expected_region_count,
            },
        )
        response.raise_for_status()

    async def fail(self, command: ExtractionCommand) -> None:
        response = await self._http.post(
            f"{self._base_url}/internal/v1/books/{command.book_id}"
            "/extraction/failed",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Idempotency-Key": f"extraction-{command.process_id}",
            },
            json={"processId": command.process_id},
        )
        response.raise_for_status()

    async def close(self) -> None:
        if self._owns_client:
            await self._http.aclose()


def _batches[T](items: tuple[T, ...], size: int) -> Iterable[tuple[T, ...]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _segment_payload(segment: ExtractedSegment) -> dict[str, object]:
    return {
        "stableKey": segment.stable_key,
        "sourceHash": segment.source_hash,
        "sequentialNumber": segment.sequential_number,
        "physicalPage": segment.physical_page,
        "bbox": _bbox_payload(segment.bbox),
        "style": segment.style.value,
        "text": segment.text,
        "translatable": segment.translatable,
    }


def _region_payload(region: ImageTextRegion) -> dict[str, object]:
    return {
        "stableKey": region.stable_key,
        "imageStableKey": region.image_stable_key,
        "sourceHash": region.source_hash,
        "sequentialNumber": region.sequential_number,
        "physicalPage": region.physical_page,
        "bbox": _bbox_payload(region.bbox),
        "text": region.text,
        "confidence": region.confidence,
    }


def _bbox_payload(bbox: BoundingBox) -> dict[str, float]:
    return {"x0": bbox.x0, "y0": bbox.y0, "x1": bbox.x1, "y1": bbox.y1}


def _extension(media_type: str) -> str:
    return "jpg" if media_type == "image/jpeg" else media_type.rsplit("/", 1)[-1]
