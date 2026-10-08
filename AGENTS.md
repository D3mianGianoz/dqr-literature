# Repository workflow

Run commands from the repository root. Keep local filesystem paths in the
ignored `.env`, not in tracked files.

## Setup

Install Python dependencies and the spaCy language model:

```bash
uv sync
uv run python -m spacy download en_core_web_md
```

Create `.env` from the example and set `LIT` to the Literature corpus
directory. In each shell session, source it with variables exported:

```bash
test -f .env || cp .env.example .env
set -a
. ./.env
set +a
```

Commands read `LIT` automatically. There is one canonical inventory:
`data/inventory.csv`, with `year,author,title,path,zotero_key,abstract`
columns. Paths are relative to the Literature root. Bibliography and
reading-log files also default to their repository paths under `data/`;
supported `--root`, `--out`, and `--inventory` options can override defaults.
`pdftotext` must be installed and available on `PATH`.

## Inventory and bibliography

Build or refresh `data/inventory.csv` from PDFs under `LIT`. A plain refresh
preserves Zotero fields for files whose relative paths have not changed:

```bash
uv run python -m related_work.inventory
```

Extract a bibliography from a thesis PDF, then match it against the inventory.
Replace the example thesis path with the file to process:

```bash
pdftotext /path/to/thesis.pdf /tmp/refs.txt
uv run python -m related_work.match_refs --refs /tmp/refs.txt
```

Matching writes `data/soa_citations.csv`. Matches marked `weak` need manual
verification. Inventory PDF paths are relative to `LIT`; do not replace them
with absolute paths.

## Paper reading

Look up a paper by author/title text, record it as read, or list reading
progress:

```bash
uv run python -m related_work.papers show "metric maze"
uv run python -m related_work.papers mark "metric maze"
uv run python -m related_work.papers todo
```

Use `show --ref NUMBER` to select a bibliography reference. The reading log is
`data/reading_log.csv`; update it through the `mark` command.

## Optional local Zotero import

Enable Zotero's local API in Settings → Advanced and keep Zotero running. Add
the optional dependency, then enrich the canonical inventory in place:

```bash
uv sync --extra zotero
uv run python -m related_work.inventory --zotero-local
```

This enriches the single `data/inventory.csv` in place, preserving all
filesystem-discovered PDFs and relative paths while adding Zotero keys and
abstracts for unambiguous matches. Unmatched and ambiguous rows keep
filename-derived metadata. The importer reads Zotero only; it does not modify
the Zotero library. A filesystem-only refresh retains Zotero metadata when a
PDF's relative path is unchanged; renaming or moving the file drops that
association.

`data/soa_citations.csv` may contain legacy `Literature/`-prefixed paths.
Paper lookup and the SoA diff normalize those to the current inventory paths.

## Tests

Run the tests from the repository root with:

```bash
uv run python -m unittest discover -s tests
```

`-W error::ResourceWarning` is optional; the suite passes without it.
