# Full-stack PDF Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a one-command local stack where frontend upload automatically extracts, translates, builds, and exposes a PDF, while preserving manual fragment translation and rebuild.

**Architecture:** Nginx is the single browser entry point and proxies `/api/v1` to `trans-api`; all workers remain internal. `trans-api` owns persistence and exposes frontend DTOs derived from books, segments, and pipeline process rows.

**Tech Stack:** Java 21/Spring Boot/PostgreSQL/MinIO, Python 3.12/FastAPI/uv, React 19/TypeScript/PrimeReact/Vite, Nginx, Docker Compose, Ollama.

**Spec:** `docs/superpowers/specs/2026-08-20-full-stack-pdf-pipeline-design.md`

## Global Constraints

- Browser traffic uses only the Nginx origin at `http://localhost:8088`.
- Demo data requires explicit `VITE_DEMO_MODE=true`; Compose always uses the real API.
- Only `trans-api` accesses PostgreSQL and MinIO.
- Worker callbacks use `INTERNAL_SERVICE_TOKEN` and internal Compose DNS.
- Automatic mode runs create → extraction → translation → build; manual mode can edit fragments and request rebuild.
- Every service package has its own Dockerfile based on a standard Linux image.
- No production behavior is added before its failing test is observed.

---

### Task 1: Persist the selected target and expose a factual book projection

**Files:**
- Modify: `trans-api/src/main/java/io/copybarca/transapi/model/Book.java`
- Modify: `trans-api/src/main/java/io/copybarca/transapi/repo/BookRepository.java`
- Modify: `trans-api/src/main/java/io/copybarca/transapi/repo/SegmentRepository.java`
- Modify: `trans-api/src/main/java/io/copybarca/transapi/service/PipelineProcessService.java`
- Create: `trans-api/src/main/java/io/copybarca/transapi/service/BookQueryService.java`
- Create: `trans-api/src/main/java/io/copybarca/transapi/dto/book/BookViewResponse.java`
- Create: `trans-api/src/main/java/io/copybarca/transapi/dto/book/BookListResponse.java`
- Modify: `trans-api/src/main/resources/db/changelog/cumulative/db.changelog-cumulative.sql`
- Test: `trans-api/src/test/java/io/copybarca/transapi/service/BookQueryServiceTest.java`
- Test: `trans-api/src/test/java/io/copybarca/transapi/service/PipelineProcessServiceTest.java`

**Interfaces:**
- Produces: `BookQueryService.list(String search, String status): BookListResponse`.
- Produces: `BookQueryService.get(Long bookId): BookViewResponse`.
- Produces: `Book.selectTargetLanguage(String language)` invoked by pipeline start.

- [ ] Write tests asserting target language is stored at start and DTO statuses/counts come from process rows and segment counts.
- [ ] Run the two new tests and verify failures caused by missing projection APIs.
- [ ] Add the nullable `target_language` migration, entity method, repository queries, immutable response records, and minimal query service.
- [ ] Re-run focused tests and then all `trans-api` tests.
- [ ] Commit as `feat(api): expose factual book status projection`.

### Task 2: Add public fragment, build, and download contracts

**Files:**
- Modify: `trans-api/src/main/java/io/copybarca/transapi/controller/BookController.java`
- Create: `trans-api/src/main/java/io/copybarca/transapi/controller/FragmentController.java`
- Create: `trans-api/src/main/java/io/copybarca/transapi/dto/fragment/FragmentResponse.java`
- Create: `trans-api/src/main/java/io/copybarca/transapi/dto/fragment/FragmentPageResponse.java`
- Create: `trans-api/src/main/java/io/copybarca/transapi/dto/fragment/SaveTranslationRequest.java`
- Create: `trans-api/src/main/java/io/copybarca/transapi/dto/process/BuildDocumentRequest.java`
- Create: `trans-api/src/main/java/io/copybarca/transapi/service/FragmentService.java`
- Create: `trans-api/src/main/java/io/copybarca/transapi/service/PublicBuildService.java`
- Test: `trans-api/src/test/java/io/copybarca/transapi/controller/PublicApiContractTest.java`
- Test: `trans-api/src/test/java/io/copybarca/transapi/service/FragmentServiceTest.java`
- Test: `trans-api/src/test/java/io/copybarca/transapi/service/PublicBuildServiceTest.java`

**Interfaces:**
- Produces: GET list/detail/translated, GET cursor fragments, PUT fragment translation, POST build.
- Produces: `FragmentService.page(bookId, language, filter, after, limit)` ordered by sequence.
- Produces: `PublicBuildService.start(bookId, language, replaceExisting)` with completion guards.

- [ ] Write MockMvc contract tests for exact paths, multipart field `originalLanguage`, JSON shapes, validation, and PDF content disposition.
- [ ] Write service tests for untranslated filtering, manual upsert/invalidation, and rebuild confirmation.
- [ ] Run focused tests and observe contract/service failures.
- [ ] Implement minimal DTOs, repository methods, services, controllers, exception mappings, and storage read response.
- [ ] Run all API tests including DB integration with Compose PostgreSQL/MinIO.
- [ ] Commit as `feat(api): add frontend book fragment and build endpoints`.

### Task 3: Make frontend use the real API in automatic and manual modes

**Files:**
- Modify: `trans-frontend/app/src/domain/types.ts`
- Modify: `trans-frontend/app/src/services/bookService.ts`
- Modify: `trans-frontend/app/src/services/bookService.test.ts`
- Modify: `trans-frontend/app/src/pages/BooksPage.tsx`
- Modify: `trans-frontend/app/src/pages/BookDetailPage.tsx`
- Modify: `trans-frontend/app/src/pages/FragmentsPage.tsx`
- Modify: `trans-frontend/app/src/pages/BuildPage.tsx`
- Modify: `trans-frontend/app/.env.example`

**Interfaces:**
- Consumes: relative `/api/v1` book, translation, fragment, build, and download endpoints from Tasks 1–2.
- Produces: `uploadBooks` performs POST book then POST translations for each selected PDF.
- Produces: polling reloads real statuses while any document is active.

- [ ] Replace demo-oriented service tests with fetch contract tests for multipart names, create/start sequence, cursor parameters, manual save, rebuild, and failures.
- [ ] Run Vitest and verify the new tests fail against the current adapter.
- [ ] Implement explicit demo selection, real relative API default, DTO-aligned requests, download URL, and polling.
- [ ] Update pages to show stage-specific factual statuses and preserve automatic loading plus manual save/rebuild.
- [ ] Run Vitest, Oxlint, TypeScript build, and commit as `feat(frontend): connect automatic and manual PDF workflows`.

### Task 4: Containerize every service package

**Files:**
- Modify: `trans-api/Dockerfile`
- Create: `PDF-extractor/Dockerfile`
- Create: `document-builder/Dockerfile`
- Create: `trans-flow/Dockerfile`
- Create: `trans-frontend/app/Dockerfile`
- Create: `trans-frontend/app/nginx.conf`
- Create: `.dockerignore` files in each build context where needed.

**Interfaces:**
- Produces images listening on API 8080, extractor 8001, builder 8002, flow 8003, and frontend 80.

- [ ] Add smoke tests that import/start each Python app and validate frontend production routing config.
- [ ] Run smoke checks first and observe missing-image/config failures.
- [ ] Add multi-stage Dockerfiles using Temurin 21, Python 3.12 slim, Node 22 Alpine, and Nginx Alpine.
- [ ] Build every image independently and run its health command.
- [ ] Commit as `build: containerize all application packages`.

### Task 5: Add the root Compose stack and gateway

**Files:**
- Create: `compose.yaml`
- Create: `.env.example`
- Create: `infra/nginx/nginx.conf`
- Create: `infra/nginx/conf.d/at.conf`
- Modify: `.gitignore`
- Modify: `README.md`

**Interfaces:**
- Produces: `docker compose up --build -d` and browser entry point `http://localhost:8088`.
- Produces: internal DNS names and shared `INTERNAL_SERVICE_TOKEN`.

- [ ] Write `scripts/check-compose.sh` assertions for required services, healthchecks, no public worker/storage ports, and gateway locations.
- [ ] Run it and verify failure because the root stack does not exist.
- [ ] Add PostgreSQL, MinIO/init, Ollama/init, all five app containers, Nginx, volumes, healthchecks, dependencies, and safe environment defaults.
- [ ] Validate with `docker compose config`, the checker, and full image build.
- [ ] Commit as `build: add one-command local translation stack`.

### Task 6: Prove automatic and manual E2E behavior

**Files:**
- Create: `scripts/make-two-page-fixture.sh`
- Create: `scripts/e2e-pdf-pipeline.sh`
- Create: `scripts/e2e-manual-translation.sh`
- Modify: `README.md`

**Interfaces:**
- Consumes: a local source PDF path and the Nginx public API.
- Produces: ignored `.e2e-work/input-two-pages.pdf` and `.e2e-work/result.pdf`.

- [ ] Write shell assertions that fail unless the source PDF remains unchanged, exactly two pages are copied, all stages complete, a fragment can be manually updated, rebuild completes, and result passes `pdfinfo`.
- [ ] Run scripts against the incomplete stack and observe expected failures.
- [ ] Implement fixture extraction, bounded polling, diagnostic log capture, download, PDF validation, manual edit, and confirmed rebuild.
- [ ] Locate an English PDF on the desktop, create the two-page copy, start the stack, and run both E2E scripts.
- [ ] Commit scripts/docs as `test: add automatic and manual PDF pipeline E2E`.

### Task 7: Final verification and handoff

**Files:**
- Modify only documentation if verification reveals inaccurate commands.

- [ ] Run Java tests with DB integration, all three Python suites, frontend test/lint/build, Compose checker/config, and Docker image builds.
- [ ] Restart from a clean Compose state without deleting persistent user data, then repeat the two-page automatic and manual E2E runs.
- [ ] Record exact image/container health, book/process identifiers, fragment counts, model name, output PDF page count, and checksums.
- [ ] Confirm `git diff --check`, clean status, and review commits.
- [ ] Use verification-before-completion and report the browser URL, commands, results, and any operational limits.
