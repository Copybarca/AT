# Single-Fragment Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Translate and persist every book fragment independently so a content-validation failure cannot stop the rest of the book.

**Architecture:** Keep the existing `segments` and `translation_drafts` tables. Change work selection to one row per model request, record every model response in an append-only `translation_attempts` table, and put exhausted content failures into `translation_review_queue` before continuing. Transport failures still stop the worker so a supervisor can restore connectivity rather than misclassifying every segment.

**Tech Stack:** Python 3 standard library, SQLite, `unittest`, Ollama HTTP API.

## Global Constraints

- Preserve all accepted drafts already stored in `translation_memory.sqlite3`.
- Use at most one Ollama request at a time for the 12B CPU model.
- Keep strict completeness validation for numbers, layout suffixes, line counts, and minimum length.
- Use three content attempts per fragment: normal, corrective, protected-number.
- After three invalid responses, mark only that fragment `needs_review` and continue.
- Do not swallow Ollama transport or JSON errors.

---

### Task 1: Per-fragment work selection

**Files:**
- Modify: `translate_memory_translategemma.py`
- Create: `tests/test_translate_memory_translategemma.py`

**Interfaces:**
- Produces: `groups(db, start, end) -> list[list[sqlite3.Row]]`, with exactly one row in every returned group.

- [ ] **Step 1: Write the failing test**

Create an in-memory SQLite database with three pending `segments` rows and assert:

```python
work = module.groups(db, 1, None)
self.assertEqual([len(group) for group in work], [1, 1, 1])
self.assertEqual([group[0]["segment_key"] for group in work], keys)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_translate_memory_translategemma.GroupsTests -v`

Expected: FAIL because rows on the same page are currently grouped together.

- [ ] **Step 3: Implement minimal grouping change**

Return `[[row] for row in rows]` from `groups` while retaining the existing SQL ordering and source-hash join.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_translate_memory_translategemma.GroupsTests -v`

Expected: PASS.

### Task 2: Attempt history and review queue

**Files:**
- Modify: `translate_memory_translategemma.py`
- Modify: `tests/test_translate_memory_translategemma.py`

**Interfaces:**
- Produces: `ensure_draft_table(db)` creating `translation_attempts` and `translation_review_queue`.
- Produces: `record_attempt(db, row, attempt_no, prompt_version, raw, issues, elapsed)`.
- Produces: `mark_needs_review(db, row, attempts, reason)`.

- [ ] **Step 1: Write failing schema and persistence tests**

Assert that accepted and rejected attempt rows retain `segment_key`, `source_hash`, `attempt_no`, raw model text, JSON issues, and elapsed seconds. Assert that review-queue insertion is idempotent for `(segment_key, source_hash)`.

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m unittest tests.test_translate_memory_translategemma.PersistenceTests -v`

Expected: FAIL because the tables and functions do not exist.

- [ ] **Step 3: Add tables and persistence helpers**

Use append-only attempts and an upserted review queue:

```sql
CREATE TABLE IF NOT EXISTS translation_attempts (
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
  segment_key TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  attempt_no INTEGER NOT NULL,
  prompt_version TEXT NOT NULL,
  response_text TEXT NOT NULL,
  issues_json TEXT NOT NULL,
  elapsed_seconds REAL NOT NULL,
  created_at TEXT NOT NULL
);
```

The review queue stores `segment_key`, `source_hash`, `attempts`, `reason`, `status='needs_review'`, and `updated_at`, with a unique key on `(segment_key, source_hash)`.

- [ ] **Step 4: Run persistence tests**

Run: `python3 -m unittest tests.test_translate_memory_translategemma.PersistenceTests -v`

Expected: PASS.

### Task 3: Corrective and protected-number attempts

**Files:**
- Modify: `translate_memory_translategemma.py`
- Modify: `tests/test_translate_memory_translategemma.py`

**Interfaces:**
- Produces: `protect_numbers(text) -> tuple[str, dict[str, str]]`.
- Produces: `restore_protected_tokens(text, mapping) -> str`.
- Produces: `translate_fragment(row, terms, attempt_callback) -> str`.
- Raises: `FragmentNeedsReview` only after all three responses fail content validation.

- [ ] **Step 1: Write failing tests for protection and retries**

Use the real failing excerpts containing `history.1 Example 5-1`, `RFC 7519`, and `RFC 9068`. Mock `call_payload` so attempt one drops `1`, attempt two still drops it, and attempt three echoes protected markers. Assert exact restoration and three callback records.

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m unittest tests.test_translate_memory_translategemma.FragmentTranslationTests -v`

Expected: FAIL because the helpers do not exist.

- [ ] **Step 3: Implement the three strategies**

Attempt one uses the ordinary single-fragment prompt. Attempt two includes the exact validation issues. Attempt three replaces numeric tokens with alphabetic sentinel tokens, explicitly asks the model to preserve them, restores their values, then runs `completeness_issues` against the original source.

- [ ] **Step 4: Run fragment tests**

Run: `python3 -m unittest tests.test_translate_memory_translategemma.FragmentTranslationTests -v`

Expected: PASS.

### Task 4: Continue after content failure

**Files:**
- Modify: `translate_memory_translategemma.py`
- Modify: `tests/test_translate_memory_translategemma.py`

**Interfaces:**
- Consumes: `translate_fragment`, `record_attempt`, and `mark_needs_review`.
- Produces: `translate(db, start, end) -> int`, counting accepted drafts while continuing past `FragmentNeedsReview`.

- [ ] **Step 1: Write failing loop tests**

Mock the first fragment to raise `FragmentNeedsReview` and the second to succeed. Assert that the first appears in `translation_review_queue`, the second appears in `translation_drafts`, and a generic `RuntimeError` from transport still propagates.

- [ ] **Step 2: Run tests to verify failure**

Run: `python3 -m unittest tests.test_translate_memory_translategemma.TranslateLoopTests -v`

Expected: FAIL because the current loop aborts on every exception.

- [ ] **Step 3: Implement failure isolation**

Catch only `FragmentNeedsReview`, persist it, print a concise diagnostic, and continue. Keep draft inserts and attempt records in short SQLite transactions. Delete a matching review-queue entry after a later successful translation.

- [ ] **Step 4: Run loop tests**

Run: `python3 -m unittest tests.test_translate_memory_translategemma.TranslateLoopTests -v`

Expected: PASS.

### Task 5: Full verification and safe process transition

**Files:**
- Modify: `КАК_ПРОДОЛЖИТЬ_ПЕРЕВОД.md`

- [ ] **Step 1: Run all unit tests and compilation**

Run: `python3 -m unittest discover -s tests -v && python3 -m py_compile translate_memory.py translate_memory_translategemma.py`

Expected: all tests PASS and compilation exits 0.

- [ ] **Step 2: Back up the live database**

Use the SQLite Backup API and verify the backup with `PRAGMA integrity_check`, expecting `ok`.

- [ ] **Step 3: Switch only at a committed fragment boundary**

Wait for the current worker to write a `draft group` line, terminate that PID gracefully, verify it exited, then launch the new worker with `--start 1`. Existing source-hash-matched drafts must be skipped.

- [ ] **Step 4: Verify live progress**

Confirm the new PID exists, each new log line reports one block, the SQLite drafted count increases, and Ollama reports the 12B model loaded.

- [ ] **Step 5: Update recovery documentation**

Document the one-fragment mode, three-attempt cap, `translation_attempts`, `translation_review_queue`, and the rule that content failures continue while transport failures stop.
