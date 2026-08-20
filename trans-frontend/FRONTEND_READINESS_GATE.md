# Frontend readiness gate

Gate status: **APPROVED**

Gate owner: **Arthur — product owner**

Approval date: **2026-08-20**

An agent must not change this status based on its own recommendations. Only the
product owner can approve the gate after all mandatory decisions are complete.

## Mandatory approvals

| Area | Required artifact or decision | Status | Approver / date |
| --- | --- | --- | --- |
| Product scope | MVP: document list/upload/detail, manual fragments, pipeline monitoring, final build/rebuild | APPROVED | Arthur / 2026-08-20 |
| Open-source stack | React 19.2.8, TypeScript 7.0.2, Vite 8.2.2, PrimeReact 10.9.8 MIT; only free OSS dependencies | APPROVED | Arthur / 2026-08-20 |
| Palette | Approved warm beige light palette from `DESIGN_SYSTEM_REQUIREMENTS.md`; dark mode excluded from MVP | APPROVED | Arthur / 2026-08-20 |
| Visual style | Content-focused professional document workspace matching `prototypes/main-flow-v1.html` | APPROVED | Arthur / 2026-08-20 |
| Typography | System UI font stack with Cyrillic/Latin coverage; no separately licensed webfont | APPROVED | Arthur / 2026-08-20 |
| Design tokens | Palette, 4px spacing grid, responsive sizes, borders, focus, motion and breakpoints documented | APPROVED | Arthur / 2026-08-20 |
| Components | PrimeReact 10 primitives wrapped by project components with loading/error/empty/disabled states | APPROVED | Arthur / 2026-08-20 |
| Screens | Current interactive prototype is the MVP screen and responsive-layout source | APPROVED | Arthur / 2026-08-20 |
| Navigation | `/books`, `/books/new`, `/books/:id`, `/fragments`, `/books/:id/fragments`, `/build` | APPROVED | Arthur / 2026-08-20 |
| HTTP API | Configurable typed adapter; real API when configured, deterministic demo adapter otherwise | APPROVED | Arthur / 2026-08-20 |
| Realtime | Optional WebSocket invalidation with reconnect; manual refresh remains required fallback | APPROVED | Arthur / 2026-08-20 |
| Security | Same-origin/HTTPS deployment, no persistent token storage, server-authoritative validation and permissions | APPROVED | Arthur / 2026-08-20 |
| Accessibility | WCAG 2.2 AA target, keyboard navigation, visible focus, semantic labels and live status messages | APPROVED | Arthur / 2026-08-20 |
| Localization | Russian UI, `Intl` formatting, English/Russian content, Russian fallback | APPROVED | Arthur / 2026-08-20 |
| Quality | TypeScript strict mode, Oxlint, Vitest critical-flow tests, production build as handoff gates | APPROVED | Arthur / 2026-08-20 |
| Operations | Static Vite build, environment-configured API/WebSocket URLs, browser diagnostics, rollback by artifact | APPROVED | Arthur / 2026-08-20 |

## Approval record

- Arthur explicitly identified himself as product owner and instructed the
  implementation gate to be removed on 2026-08-20.
- Product owner delegated engineering details not specified by the prototype.
- Only free open-source dependencies may be installed.
- Runtime integration remains configurable so unavailable backend/realtime
  contracts do not block the frontend implementation or demo mode.

## Actions allowed while blocked

- update requirements and ADRs;
- compare palettes, fonts, layouts, component libraries, and realtime options;
- produce static wireframes/prototypes outside runtime application code;
- negotiate OpenAPI and WebSocket schemas with backend owners;
- review accessibility, security, licenses, and deployment constraints.

Everything else remains prohibited by `AGENTS.md`.
