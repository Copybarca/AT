from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from document_builder.models import (
    BuildAsset,
    BuildInput,
    BuildRequest,
    ElementType,
)
from document_builder.settings import ServiceSettings


class BuildInputValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class IncomingAsset:
    asset_key: str
    filename: str
    media_type: str
    content: bytes


class BuildInputValidator:
    def __init__(self, settings: ServiceSettings) -> None:
        self._settings = settings

    def validate(
        self,
        request: BuildRequest,
        assets: tuple[IncomingAsset, ...],
    ) -> BuildInput:
        if len(request.elements) > self._settings.build_max_elements:
            raise BuildInputValidationError("Element limit exceeded")

        ordered = tuple(sorted(request.elements, key=lambda item: item.sequential_number))
        expected_numbers = list(range(1, len(ordered) + 1))
        actual_numbers = [item.sequential_number for item in ordered]
        if actual_numbers != expected_numbers:
            raise BuildInputValidationError(
                "Element sequentialNumber values must form a continuous sequence 1..N"
            )

        expected_keys = {
            item.asset_key
            for item in ordered
            if item.type is ElementType.IMAGE and item.asset_key is not None
        }
        actual_keys = [asset.asset_key for asset in assets]
        if len(actual_keys) != len(set(actual_keys)):
            raise BuildInputValidationError("Duplicate asset parts violate exact asset coverage")
        missing = expected_keys - set(actual_keys)
        extra = set(actual_keys) - expected_keys
        if missing and not extra:
            raise BuildInputValidationError(f"Missing assets: {sorted(missing)}")
        if missing or extra:
            raise BuildInputValidationError(
                f"Invalid asset coverage; missing={sorted(missing)}, extra={sorted(extra)}"
            )

        self._settings.build_temp_root.mkdir(parents=True, exist_ok=True)
        job_directory = Path(
            tempfile.mkdtemp(
                prefix=f"build-{request.process_id}-",
                dir=self._settings.build_temp_root,
            )
        )
        try:
            snapshots = tuple(
                self._snapshot_asset(index, incoming, ordered, job_directory)
                for index, incoming in enumerate(assets, start=1)
            )
            canonical = json.dumps(
                request.model_dump(by_alias=True, mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            digest = sha256(canonical.encode("utf-8"))
            for asset in sorted(snapshots, key=lambda item: item.asset_key):
                digest.update(asset.asset_key.encode("utf-8"))
                digest.update(asset.sha256.encode("ascii"))
            return BuildInput(
                request=request,
                elements=ordered,
                assets=snapshots,
                job_directory=job_directory,
                manifest_sha256=f"sha256:{digest.hexdigest()}",
            )
        except BaseException:
            shutil.rmtree(job_directory)
            raise

    def _snapshot_asset(
        self,
        index: int,
        incoming: IncomingAsset,
        elements: tuple,
        job_directory: Path,
    ) -> BuildAsset:
        if len(incoming.content) > self._settings.build_max_image_bytes:
            raise BuildInputValidationError("Image byte limit exceeded")

        element = next(item for item in elements if item.asset_key == incoming.asset_key)
        try:
            with Image.open(BytesIO(incoming.content)) as image:
                image.verify()
                image_format = image.format
                width, height = image.size
        except (UnidentifiedImageError, OSError) as error:
            raise BuildInputValidationError("Asset is not a decodable image") from error

        actual_media_type = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
        }.get(image_format or "")
        if (
            actual_media_type is None
            or incoming.media_type != actual_media_type
            or element.media_type != actual_media_type
        ):
            raise BuildInputValidationError("Declared media type does not match image bytes")
        if width * height > self._settings.build_max_image_pixels:
            raise BuildInputValidationError("Image pixel limit exceeded")

        extension = "png" if actual_media_type == "image/png" else "jpg"
        target = job_directory / f"asset-{index:04d}.{extension}"
        target.write_bytes(incoming.content)
        digest = sha256(incoming.content).hexdigest()
        return BuildAsset(
            asset_key=incoming.asset_key,
            path=target,
            media_type=actual_media_type,
            sha256=f"sha256:{digest}",
            size=len(incoming.content),
            width=width,
            height=height,
        )
