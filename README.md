# dqr-literature

Literature evidence and tooling for sensor-data-quality and anomaly-detection
research. This repository holds the inventory, reading log, paper evidence,
and cross-paper synthesis. The AUO study repository owns its questions, study
design, vocabulary, validity limits, decisions, and status. See the study's
[project-facing reference register](../jupiler-22013_auo/docs/research/references.md)
for its selected sources and why they matter.

Detailed claims and their limitations belong in `notes/papers/`; keep
`review.md` as a concise synthesis. AUO references should link here using
relative paths, assuming sibling checkouts. Keep local filesystem paths in
ignored configuration. Derive reading progress from `uv run python -m
related_work.papers todo` rather than maintaining counts in documentation.

There is one canonical inventory, `data/inventory.csv`. It indexes PDFs from
the Literature folder and can be enriched in place with Zotero metadata while
preserving filesystem coverage and relative PDF paths.

The command-line tools live in `related_work/`; tests and PDF fixtures live in
`tests/`. Start with the repository setup, inventory refresh/enrichment,
citation matching, paper-reading, and test instructions in
[`AGENTS.md`](AGENTS.md).
