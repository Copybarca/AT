from __future__ import annotations

import hmac
import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Protocol

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, status
from pydantic import ValidationError

from document_builder.callback_client import BuildCallbackClient
from document_builder.cleanup import remove_job_directory
from document_builder.input_validator import (
    BuildInputValidationError,
    BuildInputValidator,
    IncomingAsset,
)
from document_builder.models import BuildRequest
from document_builder.queue import BuildJob, BuildTaskQueue, SubmitOutcome
from document_builder.settings import ServiceSettings
from document_builder.worker import BuildWorker


class AssetTooLargeError(ValueError):
    pass


class UploadReader(Protocol):
    async def read(self, size: int) -> bytes: ...


async def stream_upload_to_path(
    upload: UploadReader,
    target: Path,
    *,
    maximum_bytes: int,
    chunk_size: int = 1024 * 1024,
) -> int:
    written = 0
    with target.open("wb") as destination:
        while chunk := await upload.read(chunk_size):
            written += len(chunk)
            if written > maximum_bytes:
                raise AssetTooLargeError("Asset exceeds configured byte limit")
            destination.write(chunk)
    return written


def create_app(
    settings: ServiceSettings | None = None,
    *,
    queue: BuildTaskQueue | None = None,
) -> FastAPI:
    configured = settings or ServiceSettings()
    callback: BuildCallbackClient | None = None
    if queue is None:
        callback = BuildCallbackClient(
            base_url=configured.trans_api_base_url,
            service_token=configured.trans_api_token,
            retries=configured.build_callback_retries,
            retry_delay_seconds=configured.build_callback_retry_delay_seconds,
        )
        queue = BuildTaskQueue(
            capacity=configured.build_queue_capacity,
            worker_count=configured.build_worker_count,
            handler=BuildWorker(settings=configured, callback_client=callback),
        )
    task_queue = queue
    validator = BuildInputValidator(configured)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await task_queue.start()
        try:
            yield
        finally:
            await task_queue.stop()
            if callback is not None:
                await callback.close()

    app = FastAPI(title="Document Builder", lifespan=lifespan)

    def require_token(authorization: str | None) -> None:
        expected = f"Bearer {configured.trans_api_token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "UP"}

    @app.post("/internal/v1/builds", status_code=status.HTTP_202_ACCEPTED)
    async def submit_build(
        request: Annotated[str, Form()],
        asset: Annotated[list[UploadFile] | None, File()] = None,
        authorization: Annotated[str | None, Header()] = None,
        idempotency_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, int | bool]:
        require_token(authorization)
        try:
            raw = json.loads(request)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=400, detail="Malformed request JSON") from error
        try:
            command = BuildRequest.model_validate(raw)
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=error.errors()) from error
        if idempotency_key != f"build-{command.process_id}":
            raise HTTPException(status_code=400, detail="Invalid Idempotency-Key")

        configured.build_temp_root.mkdir(parents=True, exist_ok=True)
        staging = Path(
            tempfile.mkdtemp(
                prefix=f"build-upload-{command.process_id}-",
                dir=configured.build_temp_root,
            )
        )
        try:
            incoming: list[IncomingAsset] = []
            total_bytes = len(request.encode("utf-8"))
            if total_bytes > configured.build_max_request_bytes:
                raise HTTPException(status_code=413, detail="Build request is too large")
            for index, upload in enumerate(asset or [], start=1):
                asset_key = upload.headers.get("x-asset-key")
                if not asset_key:
                    raise HTTPException(
                        status_code=422,
                        detail="Asset part lacks X-Asset-Key",
                    )
                available = min(
                    configured.build_max_image_bytes,
                    configured.build_max_request_bytes - total_bytes,
                )
                try:
                    size = await stream_upload_to_path(
                        upload,
                        staging / f"upload-{index:04d}",
                        maximum_bytes=available,
                    )
                except AssetTooLargeError as error:
                    raise HTTPException(
                        status_code=413,
                        detail="Build request is too large",
                    ) from error
                total_bytes += size
                incoming.append(
                    IncomingAsset(
                        asset_key=asset_key,
                        filename=upload.filename or "asset",
                        media_type=upload.content_type or "application/octet-stream",
                        source_path=staging / f"upload-{index:04d}",
                    )
                )
            try:
                snapshot = validator.validate(command, tuple(incoming))
            except BuildInputValidationError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
        finally:
            remove_job_directory(staging)
        job = BuildJob(snapshot, snapshot.manifest_sha256)
        outcome = task_queue.submit(job)
        if outcome is not SubmitOutcome.ACCEPTED:
            remove_job_directory(snapshot.job_directory)
        if outcome is SubmitOutcome.CONFLICT:
            raise HTTPException(status_code=409, detail="Conflicting process command")
        if outcome is SubmitOutcome.FULL:
            raise HTTPException(status_code=429, detail="Build queue is full")
        return {"processId": command.process_id, "accepted": True}

    return app
