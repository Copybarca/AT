# Document Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a queued service that accepts one complete document package, renders and validates a PDF, and posts the raw result to `trans-api`.

**Architecture:** The API validates multipart data into an immutable `BuildInput`. One `BuildTaskQueue` owns local jobs; a worker runs ordering, Jinja2 rendering, the sole WeasyPrint adapter, independent PyPDF validation, and an idempotent callback.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, Pillow, Jinja2, WeasyPrint, PyPDF, HTTPX, pytest.

**Spec:** `docs/superpowers/specs/2026-08-19-three-service-pipeline-design.md`

## Global Constraints

- The specialized `document-builder/TECHNICAL_SPEC.md` has precedence for builder data flow.
- All JSON and image bytes arrive in one multipart command; no manifest/assets GET is allowed.
- No database, S3, OCR, translation, second renderer, or real neural model.
- One bounded queue component owns all local scheduling state.
- Only a PDF accepted by independent validation may be posted back.
- All production behavior is introduced by a failing test first.

---

### Task 1: Input contracts, validation, and ordering

**Files:**
- Create: `document-builder/src/document_builder/models.py`
- Create: `document-builder/src/document_builder/settings.py`
- Create: `document-builder/src/document_builder/input_validator.py`
- Create: `document-builder/src/document_builder/ordering.py`
- Test: `document-builder/tests/test_input_validator.py`
- Test: `document-builder/tests/test_ordering.py`

**Interfaces:**
- Produces: frozen `BuildRequest`, `BuildElement`, `BuildAsset`, and `BuildInput`.
- Produces: `BuildInputValidator.validate(request, assets) -> BuildInput`.
- Produces: `order_and_group(elements) -> tuple[DocumentBlock, ...]`.

- [ ] Write tests for continuous `1..N`, duplicate/gap rejection, known styles/types, exact asset coverage, PNG/JPEG signature and dimensions, caption placement, heading+content grouping, list grouping, and code whitespace.
- [ ] Run focused tests and confirm missing implementation failures.
- [ ] Implement immutable models, limit checks, manifest/asset hashes, sequence validation, and typed block grouping.
- [ ] Re-run focused tests, ruff, and mypy.
- [ ] Commit as `feat(builder): validate and order build inputs`.

### Task 2: HTML, PDF rendering, and independent validation

**Files:**
- Create: `document-builder/src/document_builder/layout.py`
- Create: `document-builder/src/document_builder/html_renderer.py`
- Create: `document-builder/src/document_builder/pdf_renderer.py`
- Create: `document-builder/src/document_builder/pdf_validator.py`
- Create: `document-builder/src/document_builder/templates/book.html`
- Create: `document-builder/src/document_builder/styles/book.css`
- Test: `document-builder/tests/test_html_renderer.py`
- Test: `document-builder/tests/test_pdf_pipeline.py`

**Interfaces:**
- Consumes: ordered document blocks and local asset paths.
- Produces: `HtmlRenderer.render(build_input) -> str`.
- Produces: `PdfRenderer.render(html, asset_root, output_path) -> None`.
- Produces: `PdfValidator.validate(path, expected) -> PdfValidationReport`.

- [ ] Write tests proving HTML escaping, list and code preservation, local-only image URIs, blocked HTTP fetches, required CSS pagination rules, readable PDF output, expected page size/control text, hash, and no blank pages.
- [ ] Run focused tests and confirm they fail for missing renderer/validator.
- [ ] Implement the Jinja template/CSS, restricted WeasyPrint URL fetcher, one renderer, and PyPDF validation report.
- [ ] Run the real local WeasyPrint/PyPDF tests without external resources.
- [ ] Commit as `feat(builder): render and validate PDF documents`.

### Task 3: Queue, command API, callback, and cleanup

**Files:**
- Create: `document-builder/src/document_builder/callback_client.py`
- Create: `document-builder/src/document_builder/cleanup.py`
- Create: `document-builder/src/document_builder/queue.py`
- Create: `document-builder/src/document_builder/worker.py`
- Create: `document-builder/src/document_builder/api.py`
- Create: `document-builder/src/document_builder/app.py`
- Modify: `document-builder/src/document_builder/__init__.py`
- Modify: `document-builder/README.md`
- Test: `document-builder/tests/test_queue.py`
- Test: `document-builder/tests/test_api.py`
- Test: `document-builder/tests/test_callback_client.py`

**Interfaces:**
- Produces: `BuildTaskQueue.submit(build_input) -> SubmitResult`, lifecycle `start()/stop()`, and idempotent process registry.
- Produces: `BuildCallbackClient.send(request, pdf_path, report) -> None` using raw `application/pdf`.
- Produces: FastAPI routes `POST /internal/v1/builds` and `GET /health`.

- [ ] Write tests for auth, multipart 202, malformed JSON 400, sequence/assets 422, idempotent replay, conflict 409, full queue 429, callback host restriction, required callback headers, retrying identical bytes, and temp cleanup.
- [ ] Run focused tests and confirm missing route/client failures.
- [ ] Implement streaming-to-temp multipart handling, queue/worker lifecycle, raw callback retries, and startup/stage cleanup.
- [ ] Run `uv run pytest -q`, `uv run ruff check .`, and `uv run mypy src`.
- [ ] Commit as `feat(builder): expose queued document build API`.
