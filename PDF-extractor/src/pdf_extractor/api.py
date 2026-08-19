from __future__ import annotations

import hmac
import shutil
import tempfile
from contextlib import asynccontextmanager
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pdf_extractor.extractor import PdfExtractionService
from pdf_extractor.figures import FigureExtractor
from pdf_extractor.models import ExtractionCommand
from pdf_extractor.ocr import TesseractImageOcrEngine, TesseractOcrEngine
from pdf_extractor.queue import (
    ExtractionJob,
    ExtractionTaskQueue,
    SubmitOutcome,
)
from pdf_extractor.settings import (
    FragmentationSettings,
    RuntimeFragmentationSettings,
    ServiceSettings,
)
from pdf_extractor.text_layer import TextLayerExtractor
from pdf_extractor.trans_api_client import TransApiExtractionClient
from pdf_extractor.worker import ExtractionWorker


class FragmentationPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    min_sentences: int = Field(alias="minSentences", ge=1)
    max_sentences: int = Field(alias="maxSentences", ge=1)
    boundary_tolerance_sentences: int = Field(
        alias="boundaryToleranceSentences",
        ge=0,
    )

    def to_settings(self) -> FragmentationSettings:
        return FragmentationSettings(
            min_sentences=self.min_sentences,
            max_sentences=self.max_sentences,
            boundary_tolerance_sentences=self.boundary_tolerance_sentences,
        )


def create_app(
    settings: ServiceSettings | None = None,
    *,
    queue: ExtractionTaskQueue | None = None,
    fragmentation_provider: RuntimeFragmentationSettings | None = None,
) -> FastAPI:
    configured = settings or ServiceSettings()
    provider = fragmentation_provider or RuntimeFragmentationSettings(
        configured.fragmentation
    )
    client: TransApiExtractionClient | None = None
    if queue is None:
        client = TransApiExtractionClient(
            base_url=configured.trans_api_base_url,
            service_token=configured.service_token,
            batch_size=configured.extraction_batch_size,
        )
        extractor = PdfExtractionService(
            text_layer=TextLayerExtractor(
                min_selectable_characters=configured.min_selectable_characters
            ),
            ocr_engine=TesseractOcrEngine(
                dpi=configured.ocr_dpi,
                language=configured.ocr_language,
            ),
            figure_extractor=FigureExtractor(
                image_ocr_engine=TesseractImageOcrEngine(
                    language=configured.ocr_language,
                )
            ),
        )
        queue = ExtractionTaskQueue(
            capacity=configured.extraction_queue_capacity,
            worker_count=configured.extraction_worker_count,
            handler=ExtractionWorker(extractor, client),
        )
    task_queue = queue

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await task_queue.start()
        try:
            yield
        finally:
            await task_queue.stop()
            if client is not None:
                await client.close()

    app = FastAPI(title="PDF Extractor", lifespan=lifespan)

    def require_token(authorization: str | None) -> None:
        expected = f"Bearer {configured.service_token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "UP"}

    @app.get("/internal/v1/settings/fragmentation")
    async def get_fragmentation(
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, int]:
        require_token(authorization)
        return _fragmentation_payload(provider.snapshot())

    @app.put("/internal/v1/settings/fragmentation")
    async def put_fragmentation(
        payload: FragmentationPayload,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, int]:
        require_token(authorization)
        try:
            replacement = payload.to_settings()
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=error.errors()) from error
        return _fragmentation_payload(provider.replace(replacement))

    @app.post("/internal/v1/extractions", status_code=status.HTTP_202_ACCEPTED)
    async def submit_extraction(
        request: Annotated[str, Form()],
        file: Annotated[UploadFile, File()],
        authorization: Annotated[str | None, Header()] = None,
        idempotency_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, int | bool]:
        require_token(authorization)
        try:
            command = ExtractionCommand.model_validate_json(request)
        except ValidationError as error:
            raise HTTPException(status_code=400, detail=error.errors()) from error
        if idempotency_key != f"extraction-{command.process_id}":
            raise HTTPException(status_code=400, detail="Invalid Idempotency-Key")

        temp_directory, pdf_path, file_hash = await _store_pdf(
            file,
            configured.extraction_temp_root,
            configured.max_request_bytes,
        )
        fingerprint = sha256(
            (
                command.model_dump_json(by_alias=True)
                + ":"
                + file_hash
            ).encode("utf-8")
        ).hexdigest()
        job = ExtractionJob(
            command=command,
            pdf_path=pdf_path,
            fragmentation=provider.snapshot(),
            fingerprint=fingerprint,
            temp_directory=temp_directory,
        )
        outcome = task_queue.submit(job)
        if outcome is not SubmitOutcome.ACCEPTED:
            shutil.rmtree(temp_directory)
        if outcome is SubmitOutcome.CONFLICT:
            raise HTTPException(status_code=409, detail="Conflicting process command")
        if outcome is SubmitOutcome.FULL:
            raise HTTPException(status_code=429, detail="Extraction queue is full")
        return {"processId": command.process_id, "accepted": True}

    return app


async def _store_pdf(
    upload: UploadFile,
    temp_root: Path,
    maximum_bytes: int,
) -> tuple[Path, Path, str]:
    temp_root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="extraction-", dir=temp_root))
    target = directory / "source.pdf"
    digest = sha256()
    size = 0
    prefix = b""
    try:
        with target.open("wb") as destination:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > maximum_bytes:
                    raise HTTPException(status_code=413, detail="PDF is too large")
                if not prefix:
                    prefix = chunk[:5]
                digest.update(chunk)
                destination.write(chunk)
        if size == 0 or prefix != b"%PDF-":
            raise HTTPException(status_code=422, detail="File is not a PDF")
        return directory, target, f"sha256:{digest.hexdigest()}"
    except BaseException:
        shutil.rmtree(directory)
        raise


def _fragmentation_payload(value: FragmentationSettings) -> dict[str, int]:
    return {
        "minSentences": value.min_sentences,
        "maxSentences": value.max_sentences,
        "boundaryToleranceSentences": value.boundary_tolerance_sentences,
    }
