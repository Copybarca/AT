# Mandatory frontend design gate

These instructions apply to the entire `trans-frontend` directory.

## Hard prohibition

Do not implement, scaffold, generate, or install the frontend while
`FRONTEND_READINESS_GATE.md` has `Gate status: BLOCKED`.

While the gate is blocked, an agent must not:

- create `package.json`, a lock file, Vite/TypeScript configuration, runtime
  source files, styles, assets, Storybook, tests, containers, or CI jobs;
- install npm packages or run a project generator;
- choose colors, typography, component appearance, navigation, screen layout,
  API behavior, or realtime protocol by assumption;
- treat draft values or an agent's recommendation as product-owner approval.

Only documentation, research, ADRs, wireframes, API/event-contract proposals,
and updates to the readiness checklist are allowed while blocked.

## How the gate may be opened

Only the product owner may change `Gate status` to `APPROVED`. Before doing so,
every mandatory row in `FRONTEND_READINESS_GATE.md` must contain:

1. a concrete decision or linked artifact;
2. the approver and approval date;
3. no unresolved `TBD`, `DRAFT`, or `BLOCKED` marker.

If asked to implement before that point, stop and report the missing gate
items. Do not silently fill them in and do not create a temporary scaffold.

After approval, implementation must follow the approved ADRs and design tokens.
Any incompatible change closes the gate again until the owner approves it.
