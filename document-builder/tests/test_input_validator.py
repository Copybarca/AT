from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from document_builder.input_validator import (
    BuildInputValidationError,
    BuildInputValidator,
    IncomingAsset,
)
from document_builder.models import BuildRequest
from document_builder.settings import ServiceSettings


def png_bytes(width: int = 32, height: int = 20) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(20, 40, 180)).save(buffer, format="PNG")
    return buffer.getvalue()


def request(elements: list[dict]) -> BuildRequest:
    return BuildRequest.model_validate(
        {
            "processId": 9001,
            "bookId": 42,
            "resultCallbackUrl": "/internal/v1/books/42/build-result",
            "document": {"title": "Книга", "language": "ru"},
            "elements": elements,
        }
    )


def validator(temp_root: Path) -> BuildInputValidator:
    return BuildInputValidator(
        ServiceSettings(
            _env_file=None,
            build_temp_root=temp_root,
            build_max_elements=100,
            build_max_image_bytes=1024 * 1024,
            build_max_image_pixels=100_000,
        )
    )


def text(number: int, value: str = "Text", style: str = "BODY") -> dict:
    return {
        "sequentialNumber": number,
        "type": "TEXT",
        "text": value,
        "style": style,
    }


def image(number: int, key: str = "figure-001") -> dict:
    return {
        "sequentialNumber": number,
        "type": "IMAGE",
        "assetKey": key,
        "mediaType": "image/png",
        "altText": "Figure",
    }


def test_validator_sorts_sequence_and_creates_immutable_asset_snapshot(
    tmp_path: Path,
) -> None:
    command = request([image(2), text(1, "Heading", "HEADING_1")])
    incoming = IncomingAsset(
        asset_key="figure-001",
        filename="../../unsafe.png",
        media_type="image/png",
        content=png_bytes(),
    )

    result = validator(tmp_path).validate(command, (incoming,))

    assert [item.sequential_number for item in result.elements] == [1, 2]
    assert [asset.asset_key for asset in result.assets] == ["figure-001"]
    assert result.assets[0].path.parent == result.job_directory
    assert result.assets[0].path.name == "asset-0001.png"
    assert result.assets[0].width == 32
    assert result.assets[0].height == 20
    assert result.assets[0].sha256.startswith("sha256:")
    assert result.manifest_sha256.startswith("sha256:")


@pytest.mark.parametrize(
    "elements",
    [
        [text(1), text(3)],
        [text(1), text(1)],
    ],
)
def test_validator_rejects_gaps_and_duplicate_sequence_numbers(
    tmp_path: Path,
    elements: list[dict],
) -> None:
    with pytest.raises(BuildInputValidationError, match="continuous"):
        validator(tmp_path).validate(request(elements), ())


def test_validator_rejects_missing_and_extra_assets(tmp_path: Path) -> None:
    command = request([text(1), image(2)])

    with pytest.raises(BuildInputValidationError, match="Missing assets"):
        validator(tmp_path).validate(command, ())

    extra = IncomingAsset(
        asset_key="unused",
        filename="extra.png",
        media_type="image/png",
        content=png_bytes(),
    )
    with pytest.raises(BuildInputValidationError, match="asset coverage"):
        validator(tmp_path).validate(command, (extra,))


def test_validator_rejects_declared_mime_that_differs_from_image_bytes(
    tmp_path: Path,
) -> None:
    command = request([image(1)])
    incoming = IncomingAsset(
        asset_key="figure-001",
        filename="figure.png",
        media_type="image/jpeg",
        content=png_bytes(),
    )

    with pytest.raises(BuildInputValidationError, match="media type"):
        validator(tmp_path).validate(command, (incoming,))
