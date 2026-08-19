# Three-Service PDF Pipeline Design

## Scope

Implement the three services requested for the local PDF pipeline:

1. `PDF-extractor`: extract ordered text, code, images, and OCR regions from a PDF and publish the complete extraction to `trans-api`.
2. `document-builder`: accept a complete immutable document package, render and validate one PDF, and return it to `trans-api`.
3. `trans-api`: own PostgreSQL and S3, expose the external API, persist extraction results and process state, coordinate translation through the existing `trans-flow` HTTP contract, and submit complete build packages.

`trans-flow` itself is outside this implementation. No production environment and no real neural model are used in tests.

## Source-of-truth rules

- `dock` defines pipeline ownership, process invariants, extraction contracts, and the two-state process model.
- `document-builder/TECHNICAL_SPEC.md` is newer and more specific than the older builder flow in `dock`. It therefore wins where the documents conflict: builder receives all JSON elements and image bytes in one multipart command and performs no follow-up GET requests.
- `TRANSLATION_PIPELINE_RUNBOOK.md` supplies operational invariants and verification checks.
- Existing schema names, stable keys, and the `trans` ownership boundary are preserved.

## Shared architecture

Working services have no database or S3 credentials. Each service exposes one FastAPI application, one bounded queue component, and focused modules with a single responsibility. A queued command is atomic; a repeated identical process command is accepted idempotently, while the same process identifier with different content is rejected.

`trans-api` is the only persistent service. It uses a bounded Spring executor wrapped by a single `PipelineTaskQueue` component. PostgreSQL rows remain the source of truth after restart; local queue entries are only execution mechanisms.

Internal endpoints use a configured bearer service token. Callback paths are fixed by the receiving API or validated as relative paths under the configured `trans-api` base URL. User-supplied filenames never become filesystem paths.

## PDF-extractor

### Command API

`POST /internal/v1/extractions` accepts multipart parts:

- `request`: JSON containing positive `processId`, positive `bookId`, and the expected source SHA-256;
- `file`: a non-empty PDF;
- `Authorization: Bearer <service-token>`;
- `Idempotency-Key: extraction-<processId>`.

The whole command is validated and copied into a process-owned temporary directory before enqueue. Success returns `202 {"processId": ..., "accepted": true}`. Contract errors use 400/401/409/413/422 and a full queue uses 429.

### Extraction core

- PyMuPDF extracts spans, bbox, page, font traits, images, and reading order.
- Pages with an insufficient selectable text layer are rendered and sent through an injectable OCR adapter. Production uses pytesseract; tests use deterministic fakes and never invoke a real OCR model.
- Text is normalized without reordering. Code-like blocks are marked `CODE` and non-translatable.
- `FragmentAssembler` joins only adjacent sentences and snapshots `FragmentationSettings` when the job is accepted. Runtime changes affect only later jobs.
- Stable keys derive from physical page/block and fragment position. Source hashes are SHA-256 of normalized source text. `sequentialNumber` is global, continuous, and starts at one across text and image elements.
- Embedded images are emitted unchanged. OCR regions are separate records and never replace the source image.

### Result API calls

The extractor calls fixed `trans-api` endpoints in this order:

1. `segments:batch` with ordered text/code payloads;
2. `images` once per extracted image with JSON metadata plus raw bytes;
3. `image-regions:batch` with OCR regions;
4. `complete` with checksum, extractor version, and expected counts.

The complete callback is sent only after every prior call succeeds.

## Document-builder

### Command API

`POST /internal/v1/builds` follows `document-builder/TECHNICAL_SPEC.md`: one `request` JSON part and one `asset` part per image, identified by `X-Asset-Key`. It validates authentication, idempotency, limits, continuous sequence `1..N`, known element types/styles, safe text, exact image coverage, MIME signatures, and dimensions before returning 202.

The accepted immutable `BuildInput` contains normalized JSON, sorted frozen elements, per-asset hashes, a manifest hash, and files under a service-created temporary directory.

### Build core

- `ordering.py` verifies sequence and groups heading+content, image+caption, consecutive list items, code, and notes.
- `html_renderer.py` renders one escaped Jinja2 document and local assets only.
- `pdf_renderer.py` is the sole WeasyPrint adapter and rejects external URL fetches.
- `pdf_validator.py` independently opens the result with PyPDF, verifies readability, encryption, page count/size, control text, blank pages, unfinished markers, and image count, then calculates SHA-256 and size.
- `callback_client.py` sends the validated raw PDF body once per attempt with the required process/book/checksum/page headers. Retries resend the same bytes and never rebuild.

## Trans-api

### Persistent model

Liquibase owns both `trans` and quoted `"scheduled-processes"` schemas. The implementation adds:

- extraction, translation, and build process rows with only `IN_PROGRESS` and `COMPLETED`;
- extraction metadata needed for styles, page/bbox, source hashes, image metadata, OCR regions, and expected counts;
- translation attempt/review tables needed to distinguish accepted output, content failure, and transport failure.

Only `trans-api` reads or writes PostgreSQL and S3. Images and final PDFs are stored through `BookFileStorage`; worker services receive and return bytes over HTTP.

### External API

- `POST /api/v1/books` is one multipart operation containing PDF, optional title, and original language. It validates the PDF signature, creates the book, stores the original, and returns 201.
- `POST /api/v1/books/{bookId}/translations` idempotently creates/reuses the process chain and returns 202.
- `GET /api/v1/books/{bookId}/processes?targetLanguage=...` returns null for a stage not started, status-only extraction/build objects, and calculated translation counts/percentage.

### Internal API and orchestration

- Extraction batch endpoints upsert by book plus stable key and verify process ownership.
- Extraction completion compares expected and stored counts before marking complete.
- Translation selects the next current source position without an accepted target translation, calls `trans-flow` for one fragment, validates its marker/literals, persists attempts, and completes only with full coverage and an empty review queue.
- Builder commands contain all prepared text elements and original image bytes in one multipart request.
- `POST /internal/v1/books/{bookId}/build-result` accepts a raw PDF with process/checksum/page headers, validates checksum and PDF signature, stores it, and atomically completes the build process.
- Startup reconciliation re-enqueues `IN_PROGRESS` processes. Queue rejection leaves persistent state unchanged and retryable.

## Error handling and security

- No worker service logs document text, PDF bytes, images, or service tokens.
- Temporary paths are generated by the service and cleaned after success or controlled failure.
- Remote URL access from rendered HTML is denied.
- Queue capacities and worker counts are finite and configurable.
- Transport failures do not create review items. Content validation failures do not create new business statuses.
- Existing production or shared services are never contacted during tests.

## Test strategy

- Unit and API tests follow red-green TDD and exercise real domain components.
- Synthetic PDFs and images are generated in tests; no copyrighted book fixtures are committed.
- OCR and translation network boundaries use deterministic fakes or local HTTP stubs only.
- Real WeasyPrint/PyPDF integration tests validate locally generated PDFs.
- Final `trans-api` integration verification uses only Docker PostgreSQL and MinIO on the laptop.
- Each service gets its own verified commit in the requested order: extractor, builder, then transfer API. A final integration/documentation commit is allowed only for cross-service wiring that cannot belong to one service.
