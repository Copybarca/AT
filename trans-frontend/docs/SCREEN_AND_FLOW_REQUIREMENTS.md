# Screens, layout, and transitions

Status: **APPROVED MVP FLOW — 2026-08-20**

Current interactive proposal: `../prototypes/main-flow-v1.html`. Its choices
remain provisional until the product owner records corrections and approval.

## Proposed application shell

Desktop proposal: persistent left navigation plus a top application header.
Tablet/mobile proposal: top header plus drawer navigation. The content column
uses an approved maximum width and preserves a dedicated full-width mode for
tables and monitoring screens.

This proposal must be accepted or replaced with wireframes before coding.

Confirmed product feedback for the current prototype:

- the application header does not show a user avatar or user icon;
- multi-file upload remains on the upload screen until every selected file has
  finished uploading;
- after the whole batch succeeds, navigation returns to `/books` rather than
  opening an individual book;
- uploaded books appear in the registry without a browser reload when realtime
  updates are connected;
- without realtime updates, the registry receives them after the user invokes
  the existing manual refresh action.
- the side-navigation item is named `Список документов`, while the page heading
  remains `Документы`;
- the document registry keeps only a title search field in its toolbar; status
  filtering is performed by four clickable counters above the table: all
  documents, translating, ready, and failed;
- the selected counter is visibly active and combines with the current title
  query; no duplicate status or language dropdown is shown.
- the global `Фрагменты` navigation entry first shows a book selector populated
  from the service-backed book-list DTO; no fragment data is shown or requested
  until one book ID is selected, after which the workspace is book-scoped as
  `/books/:bookId/fragments`.

## Minimum route inventory

| Route | Purpose | Required states |
| --- | --- | --- |
| `/books` | Books list and entry point | loading, empty, populated, title search, all/translating/ready/failed counters, error |
| `/books/new` | PDF upload and metadata | idle, validating, uploading, success, failure |
| `/books/:bookId` | Book and pipeline overview | extraction, translation progress, build, completed, failed, reconnecting |
| `/books/:bookId/fragments` | Manual fragment translation in book order | loading, translated and untranslated, filtered, saving one item, save error, exhausted list |
| `/build` | Select a content-complete book and build its final document | no selection, build allowed, translation in progress, rebuild confirmation, building, replaced, cancelled, failed |
| `/books/:bookId/review` | Review/recovery if backend supports it | queue empty, items, conflict, stale source |
| `/settings` | User-visible runtime preferences | loading, saved, invalid, save error |
| catch-all | Not found | safe route back to books |

Do not implement routes that have no approved backend contract. Review and
settings may be removed from MVP explicitly rather than implemented as empty
placeholders.

## Critical flow to prototype

```text
Books list
  -> Batch upload
  -> Select one or more PDFs + metadata
  -> Confirm upload and wait for the whole batch
  -> Return to books list
       realtime connected -> new books appear automatically
       realtime unavailable -> manual refresh loads new books
  -> Open an individual book pipeline screen
       extraction -> fragment translation -> PDF build
       FAILED -> diagnosis/retry
       COMPLETED -> download translated PDF
       manual translation -> ordered fragment workspace
  -> Return to books list
```

## Manual fragment translation flow

The book has a dedicated fragment page with these owner-directed rules:

- the global fragments entry is only a book-selection landing state; the actual
  fragment list is always scoped by the selected book ID from the book-list DTO
  and there is no unscoped fragment query;
- the canonical order is always ascending `sequence`, the fragment's ordinal
  position in the whole book; client-side arrival order must never replace it;
- the only filter states are `all` and `untranslated`; `all` mixes translated
  and untranslated fragments in the same `sequence` order;
- fragments load in small batches, and reaching the sentinel near the end of
  the rendered batch requests the next batch;
- each row shows editable translation on the left and read-only original text
  on the right; an absent translation is shown as an empty editor;
- an existing translation can be edited and saved again;
- `Сохранить перевод` saves only the current fragment and exposes local
  saving, success, validation, conflict, and server-error states;
- when an item is saved under the `untranslated` filter, it leaves the visible
  list and the next eligible item is loaded without breaking sequence order.

## Final document build flow

The global `Сборка` page first requests only content-complete books: every text
fragment and image required for the book must already be stored. The page must
show four independent facts rather than one ambiguous status: content
completeness, translation-database completeness, final-PDF state, and action
availability. After choosing one book ID, behavior is:

- translation not started: `Собрать документ` is available immediately and
  starts the build without confirmation;
- translation in progress: build is disabled and the page explains that the
  active translation prevents assembly;
- translation database completed but PDF missing: primary build is available
  without replacement confirmation;
- PDF already ready: the action is `Пересобрать документ` and always opens a
  confirmation dialog warning that the existing final result will be replaced;
- confirming starts a rebuild and atomically replaces the stored final result
  only after the new build succeeds;
- declining closes the dialog, sends no build request, and shows
  `Пересборка была отменена по вашему выбору`.

The page exposes selection, disabled, confirmation, progress, success,
replacement, cancellation, conflict, and server-error states. A failed rebuild
must leave the previously completed document intact.

The prototype must define:

- which steps are pages, drawers, dialogs, or inline expansions;
- browser back/forward behavior and deep-link restoration;
- when unsaved-form warnings appear;
- focus placement after navigation and dialog close;
- transition duration and reduced-motion alternative;
- mobile stacking and overflow for tables, menus, progress, and actions;
- behavior for refresh, duplicate tabs, stale data, lost connection, and
  permission changes.

## Mandatory wireframes

For every in-scope route provide 360, 768, 1280, and 1440 px layouts, including:

- navigation open/closed;
- long title and long translated text examples;
- all pipeline statuses, including `FAILED`;
- upload validation and progress;
- empty/loading/offline/reconnecting/error states;
- success state and final PDF download action;
- keyboard focus order and major accessible labels.
