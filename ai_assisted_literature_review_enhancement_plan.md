# Implementation Plan: AI-Assisted Literature Review System

## Goal Description

Enhance the `dqr-literature` tooling to streamline literature discovery, reading prioritization, and note synthesis without brittle heuristics. Specifically:
1. **Targeted Reading Discovery**: Rapidly surface the most relevant unread papers for overhead crane sensor fault detection from the 328 unread candidates using spaCy semantic vector ranking.
2. **Ground-Truth Metadata & Annotations**: Ingest real Zotero collections and extract actual user highlights and page notes directly from Zotero's local API into paper notes.
3. **Robustness & Test Integrity**: Remove fragile test assertions and adhere strictly to repository boundary rules (`AGENTS.md`).

---

## Phase 1 — ✅ DONE (branch `feat/ai-review-phase1`)

All components implemented and committed. 35 tests passing.

### What was built

| Component | File | Status |
|---|---|---|
| Fix fragile test assertion | `tests/test_paths.py` | ✅ |
| Semantic vector recommender | `related_work/semantic.py` | ✅ |
| Local Zotero API client | `related_work/zotero.py` | ✅ |
| CLI `recommend` + `annotations` subcommands | `related_work/papers.py` | ✅ |
| Vector cache (mtime-aware, isolated in tests) | `data/.vector_cache.npz` | ✅ |
| Unit tests for semantic, Zotero, CLI paths | `tests/test_semantic.py`, `tests/test_zotero.py` | ✅ |

### Ponytail fixes applied

| Fix | Description |
|---|---|
| Fix 1 | Test suite no longer overwrites production vector cache |
| Fix 2 | Removed dead `col_map` + unused `ZoteroClient` import from `recommend` |
| Fix 3 | Reduced triple full-library Zotero fetch to at most one per `annotations` call |
| Fix 4 | Added annotation-mapping, cache-hit, and CLI tests |

### Usage

```bash
# Find most relevant unread papers for a query
uv run python -m related_work.papers recommend "overhead crane sensor fault" --limit 5

# Fetch your Zotero highlights for a paper
uv run python -m related_work.papers annotations "donne and davis"
uv run python -m related_work.papers annotations --ref 20
```

---

## Phase 2 — ✅ DONE: Note Scaffolding from Zotero Highlights

### Goal

A new `papers scaffold` CLI command that auto-generates a starter `notes/papers/<slug>.md` from a paper's Zotero highlights + PDF abstract, ready to edit. Eliminates the manual copy-paste from Zotero reader into a note file.

Implemented in `related_work/papers.py` (new `scaffold` subcommand, helper functions, and a `NOTES` path in `related_work/config.py`), with 5 unit tests in `tests/test_scaffold.py`.

### What it does

```bash
uv run python -m related_work.papers scaffold "donne and davis"
uv run python -m related_work.papers scaffold --ref 20
```

1. Looks up the paper via the existing `find()` function (SoA refs + inventory).
2. Extracts the abstract (or extractive fallback) from the PDF using `pdftotext` + spaCy — same logic as `show`.
3. Fetches Zotero highlights, underlines, and comments from the local API — same logic as `annotations`.
4. Writes `notes/papers/<slug>.md` with this template:

```markdown
# Author (Year) — Title

> **Abstract / Summary**
> <extracted abstract or top-3 sentences>

## Zotero highlights

1. Page N (highlight):
   > "quoted text"
   *Note: user comment if any*

2. …

## Notes

<!-- your notes here -->
```

5. **Safe by default**: skips silently if the file already exists (use `--force` to overwrite).
6. **Graceful offline**: if Zotero is unavailable, writes the stub without highlights, noting `<!-- Zotero unavailable — add highlights manually -->`.
7. Prints the path of the written file so you can open it immediately.

### Files to change

| File | Change |
|---|---|
| `related_work/papers.py` | Add `scaffold()` function + `scaffold` subcommand in `main()` |
| `tests/test_semantic.py` or new `tests/test_scaffold.py` | Unit test: scaffold writes correct file; skips existing; works offline |

### Design decisions (ponytail)

- **Reuse everything**: `find()`, `show()`'s PDF+spaCy path, `annotations()`'s Zotero path — no new modules.
- **No template engine**: plain f-string; the format is fixed and simple.
- **Notes dir**: defaults to `REPO / "notes" / "papers"` from `config.py` (REPO already defined). No new config needed.
- **`--force`** flag: one line in argparse; existing file check is one `if` statement.
- **What's skipped**: no auto-update of `notes/papers/README.md` (user maintains that manually). No batch scaffolding — one paper at a time, predictable.

### Verification plan

```bash
# Manual test: scaffold a paper with Zotero highlights
uv run python -m related_work.papers scaffold "donne and davis"
# → prints "already exists: notes/papers/donne-davis-2026-...
# (use --force to overwrite)"

uv run python -m related_work.papers scaffold "scholl" --force
# → writes notes/papers/scholl-spiegler-et-al-2023-...

# Automated tests
uv run python -m unittest discover -s tests
# → 40 tests OK (35 existing + 5 new for scaffold)
```

Manual checks passed: `scaffold "donne and davis"` skips existing notes and prints their path; `scaffold "scholl" --force` generates a complete note (PDF summary + Zotero highlights); and `scaffold "cichy-rass"`-style queries resolve correctly through the existing `find()` lookup.

---

## Phase 3 — ⏳ DEFERRED: Custom Taxonomy / Concept Matrix

User confirmed: *"Not at this stage."* Revisit once Phase 2 note scaffolding has been used in practice and the crane-study scope is clearer.

---

## Branch

All work lives on `feat/ai-review-phase1`. Phase 2 will be committed to the same branch before merging to `main`.
