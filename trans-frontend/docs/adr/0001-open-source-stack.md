# ADR 0001: Open-source frontend baseline

Status: **ACCEPTED — Arthur / 2026-08-20**

Date researched: 2026-08-20

## Context

The product requires PrimeReact, TypeScript, and open-source dependencies.
PrimeReact 11 is the current feature line, but it moved to the PrimeUI licensing
model. Existing PrimeReact 10 releases remain MIT-licensed, and `10.9.8` is the
last release in the archived open-source repository.

## Decision

Pin the first implementation to:

- `primereact@10.9.8`;
- `react@19.2.8` and `react-dom@19.2.8`;
- `typescript@7.0.2`;
- `vite@8.2.2` and `@vitejs/plugin-react@6.1.0`;
- `react-router@8.3.0`.

Do not use caret ranges for these architectural packages in the first lock
file. Exact transitive versions are captured in the committed lock file.

## Why not PrimeReact 11

It is not selected because the stated requirement is open-source libraries.
The free/community availability of a package is not equivalent to an
open-source license. Moving to PrimeReact 11 therefore requires a separate
license decision and owner approval.

## Consequences

- PrimeReact 10 is mature and preserves MIT licensing.
- Its upstream repository is archived, so fixes and security maintenance are a
  project risk.
- PrimeReact 10.9.8 declares React 19 in its peer dependency range, so the
  current stable React 19.2.8 pairing is selected and verified by tests/build.
- Current stable TypeScript 7 and Vite 8 are selected; nightly/canary releases
  remain excluded.
- If the owner rejects the archive risk, evaluate an actively maintained,
  OSI-approved alternative before implementation. Do not silently switch to
  PrimeReact 11.

## Implementation verification

The implementation must verify:

1. license texts for every direct and transitive dependency;
2. current vulnerability advisories for PrimeReact 10.9.8 and build tooling;
3. React 19 compatibility with the chosen router and test stack;
4. representative PrimeReact DataTable, FileUpload, Dialog, Dropdown, Toast,
   ProgressBar, Menu, and accessibility behavior;
5. production build, bundle size, keyboard navigation, and SSR requirements;
6. an exit strategy if PrimeReact 10 becomes untenable.

## Primary references

- PrimeReact 10.9.8 release: https://github.com/primefaces/primereact/releases/tag/10.9.8
- Archived PrimeReact repository and MIT license:
  https://github.com/primefaces/primereact
- PrimeReact package versions: https://www.npmjs.com/package/primereact?activeTab=versions
- React versions: https://react.dev/versions
- TypeScript package versions: https://www.npmjs.com/package/typescript?activeTab=versions
- Vite supported releases: https://vite.dev/releases
