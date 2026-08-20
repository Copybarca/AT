# Design system requirements

Status: **APPROVED FOR MVP IMPLEMENTATION — 2026-08-20**

Arthur approved the beige light visual direction and delegated remaining MVP
engineering details. Dark mode is excluded from the MVP.

## Visual direction to select

Choose exactly one documented direction and attach reference screens:

- restrained professional operations console;
- content-focused publishing workspace;
- another owner-approved direction.

The decision must define visual density, brand character, use of illustration,
light/dark mode, data density, and whether the interface should feel primarily
like an admin console or a guided document workflow.

## Palette deliverable

Provide tokens for at least:

- `surface-0` through elevated/overlay surfaces;
- page, card, input, hover, selected, disabled, and skeleton backgrounds;
- primary action and its hover/active/focus/disabled states;
- neutral text, muted text, inverse text, links, and visited links;
- border, divider, focus ring, and overlay scrim;
- semantic info, success, warning, error, and `FAILED` process states;
- extraction, translation, and build stage identities if they use distinct
  colors;
- light and dark variants, or an explicit decision that dark mode is excluded.

Every foreground/background pair must include measured contrast evidence.

### Owner-directed beige prototype palette

The current prototype uses a warm beige editorial direction rather than a blue
admin-console palette. These concrete light-theme tokens are selected for the
next design review; dark-mode inclusion is still unresolved, so this does not
open the palette gate by itself.

| Role | Token value |
| --- | --- |
| Primary text | `#312A22` |
| Muted text | `#75695C` |
| Page background | `#F3EDE3` |
| Main surface | `#FFFDF8` |
| Elevated beige surface | `#EEE3D4` |
| Border | `#DED2C2` |
| Strong border | `#AD9B85` |
| Primary action | `#76543A` |
| Primary hover | `#5C3F2B` |
| Navigation | `#322C25` |
| Navigation selected | `#4A4035` |
| Success | `#3F6A52` |
| Warning | `#91651F` |
| Error | `#9F4035` |

Measured WCAG contrast for principal prototype pairs:

| Pair | Contrast |
| --- | ---: |
| Primary text / main surface | `13.91:1` |
| Muted text / main surface | `5.25:1` |
| White / primary action | `6.78:1` |
| White / primary hover | `9.54:1` |
| Navigation text `#EADFCE` / navigation | `10.47:1` |
| White / success | `6.19:1` |
| White / error | `6.44:1` |

Focus-ring contrast, disabled controls, charts, every badge combination, and
the dark-mode decision still require the full accessibility review.

## Typography deliverable

Select open-licensed fonts with Latin and Cyrillic coverage. Specify:

- display, heading, body, label, caption, code, and numeric-progress styles;
- font size, weight, line height, letter spacing, and truncation/wrapping rules;
- maximum readable line length and long Russian/English label behavior.

## Proposed spacing grid for approval

Base grid: `4px`. Proposed tokens:

| Token | Value |
| --- | ---: |
| `space-0` | 0 |
| `space-1` | 4px |
| `space-2` | 8px |
| `space-3` | 12px |
| `space-4` | 16px |
| `space-5` | 24px |
| `space-6` | 32px |
| `space-7` | 48px |
| `space-8` | 64px |

Proposed component measurements requiring design review:

| Element | Height / minimum | Internal padding | External gap |
| --- | --- | --- | --- |
| Text input / dropdown / calendar | 40px | 0 12px | label 8px; next field 16px |
| Compact table control | 32px | 0 8px | 8px |
| Primary/secondary button | 40px | 0 16px | icon 8px; button group 8px |
| Large primary action | 48px | 0 20px | icon 8px |
| Menu item | min 40px | 10px 12px | sibling 4px |
| Menu/popup container | auto | 8px | anchor 4px |
| Desktop menubar | 56px | 0 24px | item 8px |
| Application header | 64px | 0 24px | section 16px |
| Footer | min 56px | 16px 24px | item 16px |
| Page content | auto | desktop 24px; tablet 16px; mobile 12px | sections 32px |
| Card/panel | auto | desktop 24px; mobile 16px | inner groups 16px |
| Dialog | content-based | 24px | actions 8px |
| Toast/inline message | min 48px | 12px 16px | icon 12px |

Also approve control density modes, border radius scale, borders, shadows,
z-index layers, breakpoints, animation durations, reduced-motion behavior, and
touch-target minimums. No feature code may use arbitrary pixel values outside
the approved tokens.

## Required shared component templates

Create and approve a visual/state catalog before feature screens:

- `AppShell`, `AppHeader`, `SideNavigation`, `MobileNavigation`, `AppFooter`;
- `PageHeader`, breadcrumbs, action toolbar, content section, card, divider;
- `FormField`, text input, textarea, dropdown, language selector, file upload;
- primary, secondary, tertiary, icon, danger, and link buttons;
- table/list, pagination, filters, sorting, selection, empty and loading rows;
- status badge, pipeline stepper, progress summary, progress bar, timestamp;
- inline message, toast, error summary, confirmation and destructive dialogs;
- skeleton, spinner, empty state, not-found, offline, reconnecting, and fatal
  error templates;
- download action, retry action, and `FAILED` recovery panel.

PrimeReact components should be wrapped by these project templates where a
consistent product contract is needed. Feature code must not invent local
spacing, colors, or incompatible component variants.

For every component approve default, hover, focus-visible, active, selected,
disabled, loading, invalid, read-only, empty, and high-content states as
applicable.
