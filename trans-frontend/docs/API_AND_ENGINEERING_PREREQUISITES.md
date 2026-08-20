# API and engineering prerequisites

Status: **APPROVED FOR MVP IMPLEMENTATION — configurable real/demo adapters**

## Backend contracts required

Publish and approve OpenAPI definitions for:

- multipart PDF upload, metadata, language code format, size limits, checksum,
  validation errors, and idempotency;
- translation start/retry and conflict semantics;
- process snapshot with extraction, translation counts/percent, build, and
  `FAILED` details suitable for users;
- book list and book detail retrieval; every list item must expose the stable
  database-backed book ID needed for detail and fragment navigation; the list
  contract must support title search plus all/translating/ready/failed status
  filtering and return the four corresponding total counters;
- final PDF metadata and authenticated download;
- build-page book selection returning only books with all required text
  fragments and images loaded, together with book ID, content counts,
  translated/total fragment counts, an explicit translation-database status,
  and an independent final-PDF status plus existing final-document metadata;
- final-document build/rebuild by book ID; the request must explicitly
  distinguish ordinary build from confirmed replacement of an existing result;
- review queue and manual resolution, or an explicit MVP exclusion;
- ordered fragment retrieval for a book with cursor pagination based on
  `sequence`, a small configurable batch limit, and exactly the filter modes
  `all` and `untranslated`;
- single-fragment translation upsert accepting the translation to persist and
  returning the saved fragment, including its stable ID, `sequence`, original
  text, translated text, and concurrency/version metadata;
- authentication, authorization, logout/session expiry, CORS, and error shape.

The fragment-list contract must guarantee ascending `sequence` across page
boundaries and provide an unambiguous continuation cursor such as
`afterSequence`; offset pagination is not sufficient if concurrent saves can
change the filtered result. The save contract must define empty-text
validation, overwrite permission, optimistic-concurrency conflict, idempotent
retry, and user-safe error responses. The exact public HTTP paths remain a
backend-owner decision; the prototype must not invent a production endpoint.
Every fragment read or write is book-scoped and must verify that the requested
fragment belongs to the `{bookId}`; no public unscoped fragment-list operation
is part of this flow.

The build contract must reject requests while the translation database is still
being populated. Translation completeness and final-PDF existence are separate
fields and must never be inferred from one another. A complete translation
database with no PDF is an ordinary first build; if a completed final document
already exists, the backend must reject an ordinary build and require an
explicit replacement flag or dedicated rebuild operation;
frontend confirmation alone is not sufficient protection. Replacement must be
transactional/atomic: keep the old database metadata and file reference until
the new document is successfully built and stored, then switch them together.
Define idempotency, concurrent-build conflict, progress/status retrieval,
failure recovery, audit fields, and the WebSocket event that invalidates the
book/build views. Cancelling the confirmation dialog is a client-only action
and must not call the build endpoint.

The current backend does not yet expose every required public operation, in
particular a complete book retrieval/download contract and public realtime
contract. Do not work around missing APIs by connecting the browser to MinIO or
internal service endpoints.

## Frontend architecture decisions required

- router and route-level code splitting;
- server-state library and cache key/invalidation policy;
- local UI state boundaries; avoid a global store without a concrete need;
- form and schema validation libraries;
- generated versus handwritten API types;
- WebSocket/realtime store boundary;
- error normalization and user-safe messages;
- localization framework and message ownership;
- date, number, percent, duration, and byte-size formatting;
- CSS/theming approach compatible with the approved PrimeReact 10 design;
- icon source and license;
- package manager, Node LTS version, exact lock-file policy, and update cadence.

All selected libraries must be open-source, actively assessed, pinned, and
recorded with license and maintenance ownership.

## Quality and acceptance decisions required

- unit-test boundaries and minimum critical coverage;
- component interaction tests and accessibility automation;
- API contract tests using generated fixtures or a mock server;
- E2E cases for upload, live progress, disconnect/reconnect, failure/retry, and
  PDF download;
- visual regression viewports and allowed diff policy;
- performance budgets for initial JS/CSS, route chunks, large tables, and live
  update frequency;
- supported browsers/devices and network degradation profile;
- logging, metrics, trace/correlation IDs, error reporting, privacy/redaction;
- CI gates for format, lint, types, tests, vulnerabilities, and licenses;
- environment configuration, reverse proxy, base URL, TLS, CSP, caching, and
  release/rollback process.

## Definition of ready to scaffold

The frontend is ready to scaffold only when:

1. `FRONTEND_READINESS_GATE.md` is owner-approved;
2. the design system and screen prototype are approved;
3. backend HTTP and realtime contracts are testable;
4. the dependency/license ADR is accepted;
5. the first vertical slice and its acceptance tests are written;
6. no implementation decision depends on an unresolved assumption.
