# PDF Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an asynchronous PDF extraction service that emits deterministic ordered extraction data to `trans-api`.

**Architecture:** A FastAPI boundary validates and snapshots a PDF command into a local job. One `ExtractionTaskQueue` owns bounded scheduling and workers; a focused `PdfExtractionService` delegates text-layer parsing, OCR, image extraction, fragmentation, and result publication.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, asyncio, PyMuPDF, Pillow, pytesseract, HTTPX, pytest.

**Spec:** `docs/superpowers/specs/2026-08-19-three-service-pipeline-design.md`

## Global Constraints

- No PostgreSQL or S3 dependency in this service.
- No real OCR or neural model is invoked by tests.
- Every accepted job snapshots fragmentation settings.
- One bounded queue component owns all local scheduling state.
- Result completion is published only after all batches and assets succeed.
- All production behavior is introduced by a failing test first.

---

### Task 1: Contracts, settings, and deterministic fragmentation

**Files:**
- Create: `PDF-extractor/src/pdf_extractor/models.py`
- Create: `PDF-extractor/src/pdf_extractor/settings.py`
- Create: `PDF-extractor/src/pdf_extractor/fragmentation.py`
- Test: `PDF-extractor/tests/test_fragmentation.py`
- Test: `PDF-extractor/tests/test_settings.py`

**Interfaces:**
- Produces: `FragmentationSettings(min_sentences, max_sentences, boundary_tolerance_sentences)`.
- Produces: `RuntimeFragmentationSettings.snapshot() -> FragmentationSettings` and atomic `replace(...)`.
- Produces: `FragmentAssembler.assemble(blocks, settings) -> tuple[ExtractedSegment, ...]`.
- Produces: typed extraction command, bbox, style, segment, image, region, manifest, and accepted-response models.

- [ ] Write tests showing invalid ranges are rejected, runtime replacement is atomic, a previous snapshot is unchanged, sequences are continuous, and concatenated output preserves source sentence order.
- [ ] Run `uv run pytest tests/test_settings.py tests/test_fragmentation.py -q` and confirm failures are missing modules/types.
- [ ] Implement the models, thread-safe provider, sentence splitting, natural-boundary selection, SHA-256 source hashes, and deterministic stable keys.
- [ ] Re-run the focused tests, then `uv run ruff check .` and `uv run mypy src`.
- [ ] Commit as `feat(extractor): add extraction contracts and fragmentation`.

### Task 2: Text, OCR, and image extraction core

**Files:**
- Create: `PDF-extractor/src/pdf_extractor/text_layer.py`
- Create: `PDF-extractor/src/pdf_extractor/ocr.py`
- Create: `PDF-extractor/src/pdf_extractor/figures.py`
- Create: `PDF-extractor/src/pdf_extractor/extractor.py`
- Test: `PDF-extractor/tests/test_text_layer.py`
- Test: `PDF-extractor/tests/test_extractor.py`

**Interfaces:**
- Consumes: immutable fragmentation snapshot and extraction models from Task 1.
- Produces: `TextLayerExtractor.extract_page(document, page_number) -> PageExtraction`.
- Produces: `OcrEngine.extract_page(page) -> tuple[RawTextBlock, ...]`; production adapter is `TesseractOcrEngine`.
- Produces: `FigureExtractor.extract_page(document, page_number) -> tuple[ExtractedImage, ...]`.
- Produces: `PdfExtractionService.extract(pdf_path, command, fragmentation) -> ExtractionResult`.

- [ ] Write synthetic-PDF tests for selectable text, mixed page ordering, code classification, source hash stability, embedded PNG extraction, and OCR fallback through a deterministic fake engine.
- [ ] Run the focused tests and confirm they fail because the core adapters do not exist.
- [ ] Implement page text quality detection, span/bbox/style parsing, code heuristics, injectable OCR, unchanged image bytes, and global continuous sequence assignment.
- [ ] Re-run focused tests and the complete extractor test suite.
- [ ] Commit as `feat(extractor): implement PDF extraction core`.

### Task 3: Queue, API, and trans-api publisher

**Files:**
- Create: `PDF-extractor/src/pdf_extractor/trans_api_client.py`
- Create: `PDF-extractor/src/pdf_extractor/queue.py`
- Create: `PDF-extractor/src/pdf_extractor/worker.py`
- Create: `PDF-extractor/src/pdf_extractor/api.py`
- Create: `PDF-extractor/src/pdf_extractor/app.py`
- Modify: `PDF-extractor/src/pdf_extractor/__init__.py`
- Modify: `PDF-extractor/README.md`
- Test: `PDF-extractor/tests/test_queue.py`
- Test: `PDF-extractor/tests/test_api.py`
- Test: `PDF-extractor/tests/test_trans_api_client.py`

**Interfaces:**
- Consumes: `PdfExtractionService` and typed extraction result.
- Produces: `TransApiExtractionClient.publish(result) -> None` with ordered batch/image/region/complete calls.
- Produces: `ExtractionTaskQueue.submit(job) -> SubmitResult`, lifecycle `start()/stop()`, and idempotent process registry.
- Produces: FastAPI routes `POST /internal/v1/extractions`, `GET/PUT /internal/v1/settings/fragmentation`, and `GET /health`.

- [ ] Write API tests for 202, bearer auth, PDF signature, idempotent replay, conflicting replay, full queue, invalid fragmentation update, and immutable job snapshots.
- [ ] Write a local HTTP-stub test proving completion is the final callback and is absent after a failed batch.
- [ ] Run focused tests and confirm expected missing-route/client failures.
- [ ] Implement secure temporary upload, queue ownership, worker lifecycle, HTTPX publication, callback retries, and cleanup.
- [ ] Run `uv run pytest -q`, `uv run ruff check .`, and `uv run mypy src`.
- [ ] Commit as `feat(extractor): expose queued extraction API`.
