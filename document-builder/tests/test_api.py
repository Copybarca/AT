import json
from pathlib import Path

from fastapi.testclient import TestClient

from document_builder.api import create_app
from document_builder.queue import BuildJob, BuildTaskQueue
from document_builder.settings import ServiceSettings


def command(process_id: int = 9, text: str = "Body") -> str:
    return json.dumps(
        {
            "processId": process_id,
            "bookId": 42,
            "resultCallbackUrl": "/internal/v1/books/42/build-result",
            "document": {"title": "Book", "language": "ru"},
            "elements": [
                {
                    "sequentialNumber": 1,
                    "type": "TEXT",
                    "text": text,
                    "style": "BODY",
                }
            ],
        }
    )


def settings(temp_root: Path) -> ServiceSettings:
    return ServiceSettings(
        _env_file=None,
        trans_api_token="secret",
        build_temp_root=temp_root,
        build_queue_capacity=2,
        build_worker_count=1,
    )


def test_build_api_accepts_identical_command_once(tmp_path: Path) -> None:
    received: list[BuildJob] = []

    async def handler(job: BuildJob) -> None:
        received.append(job)

    queue = BuildTaskQueue(capacity=2, worker_count=1, handler=handler)
    app = create_app(settings(tmp_path), queue=queue)

    with TestClient(app) as client:
        response = client.post(
            "/internal/v1/builds",
            headers={
                "Authorization": "Bearer secret",
                "Idempotency-Key": "build-9",
            },
            data={"request": command()},
        )
        replay = client.post(
            "/internal/v1/builds",
            headers={
                "Authorization": "Bearer secret",
                "Idempotency-Key": "build-9",
            },
            data={"request": command()},
        )

    assert response.status_code == 202
    assert response.json() == {"processId": 9, "accepted": True}
    assert replay.status_code == 202
    assert len(received) == 1


def test_build_api_rejects_unauthorized_malformed_and_conflicting_commands(
    tmp_path: Path,
) -> None:
    async def handler(_: BuildJob) -> None:
        return None

    queue = BuildTaskQueue(capacity=2, worker_count=1, handler=handler)
    app = create_app(settings(tmp_path), queue=queue)

    with TestClient(app) as client:
        unauthorized = client.post(
            "/internal/v1/builds",
            data={"request": command()},
        )
        malformed = client.post(
            "/internal/v1/builds",
            headers={
                "Authorization": "Bearer secret",
                "Idempotency-Key": "build-9",
            },
            data={"request": "not json"},
        )
        accepted = client.post(
            "/internal/v1/builds",
            headers={
                "Authorization": "Bearer secret",
                "Idempotency-Key": "build-9",
            },
            data={"request": command()},
        )
        conflict = client.post(
            "/internal/v1/builds",
            headers={
                "Authorization": "Bearer secret",
                "Idempotency-Key": "build-9",
            },
            data={"request": command(text="Changed")},
        )

    assert unauthorized.status_code == 401
    assert malformed.status_code == 400
    assert accepted.status_code == 202
    assert conflict.status_code == 409

class ChunkedUpload:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = iter(chunks)
        self.read_sizes: list[int] = []

    async def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        return next(self._chunks, b"")


def test_asset_upload_is_streamed_in_bounded_chunks(tmp_path: Path) -> None:
    import asyncio

    from document_builder.api import AssetTooLargeError, stream_upload_to_path

    target = tmp_path / "upload.bin"
    upload = ChunkedUpload([b"a" * 4, b"b" * 4, b""])

    written = asyncio.run(
        stream_upload_to_path(upload, target, maximum_bytes=8, chunk_size=4)
    )

    assert written == 8
    assert target.read_bytes() == b"a" * 4 + b"b" * 4
    assert upload.read_sizes == [4, 4, 4]

    too_large = ChunkedUpload([b"a" * 4, b"b" * 4, b"c"])
    try:
        asyncio.run(
            stream_upload_to_path(
                too_large,
                tmp_path / "too-large.bin",
                maximum_bytes=8,
                chunk_size=4,
            )
        )
    except AssetTooLargeError:
        pass
    else:
        raise AssertionError("Streaming limit must stop an oversized asset")
