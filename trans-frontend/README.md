# trans-frontend

Status: **IMPLEMENTATION APPROVED — 2026-08-20**.

This directory prepares a single web frontend for the AT translation pipeline.
The product owner approved implementation using only free open-source
dependencies. Read `AGENTS.md` and `FRONTEND_READINESS_GATE.md` before changing
the application or its approved product behavior.

The runtime application lives in `app/`:

```bash
cd app
npm install
npm run check
npm run dev
```

Interactive draft: `prototypes/main-flow-v1.html`. Open it directly in a
browser to review the registry, multi-file upload, metadata, translation
monitoring, failure/retry, and PDF download transitions. It is a discussion
artifact only and does not open the implementation gate.

## Intended product scope

The frontend must support the complete user flow:

1. upload a source PDF and metadata;
2. start a target-language translation;
3. monitor extraction, per-fragment translation, failures, retry, and PDF build;
4. show `translatedFragments / totalFragments` and the three pipeline stages;
5. provide review/recovery actions when the backend exposes them;
6. download the validated translated PDF when the build is complete.

The browser should normally communicate only with the public `trans-api`
contract. `PDF-extractor`, `trans-flow`, and `document-builder` expose internal
service APIs and should be represented through an aggregated `trans-api`
status/realtime contract, not called directly from a browser. This boundary is
still subject to explicit architecture approval.

## Selected baseline stack

The following is the recommended open-source baseline as of 2026-08-20:

| Package | Pinned baseline | Reason |
| --- | --- | --- |
| PrimeReact | `10.9.8` | Last established MIT release; do not upgrade to v11 automatically because its licensing model changed |
| React / React DOM | `19.2.8` | Current stable MIT release, supported by PrimeReact 10.9.8 peer dependencies |
| TypeScript | `7.0.2` | Current stable Apache-2.0 release |
| Vite | `8.2.2` | Current stable MIT build-tool release |

These versions are the accepted implementation baseline. Arthur accepted the
archived PrimeReact 10 maintenance risk to preserve the MIT license. All other
libraries must have an approved open-source license and pass license/security
review.

See `docs/adr/0001-open-source-stack.md` for the rationale and upgrade policy.

## Required decisions before implementation

- product audience, supported workflows, roles, and permissions;
- color palette, light/dark behavior, typography, iconography, and visual style;
- design tokens and exact spacing/sizing rules for every shared component;
- common component templates and allowed PrimeReact variants;
- responsive application shell, screen wireframes, and navigation transitions;
- HTTP API inventory, file limits, error format, authentication, CORS, and PDF
  download contract;
- WebSocket ownership, endpoint, authentication, event schema, ordering,
  reconnect/resume rules, heartbeat, and polling fallback;
- state/data/form strategy, URL state, caching, retries, and invalidation;
- accessibility target, browser/device matrix, localization, date/number rules;
- loading, empty, error, offline, reconnecting, failed, and partial-progress UX;
- test strategy, observability, performance budgets, deployment, CSP, and
  dependency/license maintenance policy.

The canonical checklist is `FRONTEND_READINESS_GATE.md`.
