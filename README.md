# dqr-literature

Literature exploration for the sensor-data-quality / anomaly-detection work on
Rolbrug Zuid crane strain data.

This repository holds the **evidence**: what has been read, what it claims, and
what has not been read yet. It is deliberately separate from
`jupiler-22013_auo`, which holds the **project**: the detection pipeline, the
fault vocabulary, and the research questions the evidence supports.

The project keeps a compact register of what it cites — see
`jupiler-22013_auo/docs/research/references.md`.

## Layout

```
review.md                  the synthesis: what each body of work says and
                           what it means for the detection study
data/inventory.csv         385 papers: year, author, title, absolute path
data/soa_citations.csv     the USES2 D3.1 bibliography matched to that index
data/reading_log.csv       which papers were actually read
scripts/related_work/      the tools that build and query the above
```

## Tools

Run from this repository's root.

```bash
# set these to your local values
PY=<path-to-jupiler-venv>/bin/python
LIT=<path-to-Literature>

$PY -m scripts.related_work.inventory --root "$LIT" --out data/inventory.csv
pdftotext <thesis.pdf> /tmp/refs.txt
$PY -m scripts.related_work.match_refs --refs /tmp/refs.txt \
    --inventory data/inventory.csv --out data/soa_citations.csv
$PY -m scripts.related_work.papers show "metric maze"   # compact abstract
$PY -m scripts.related_work.papers mark "metric maze"   # record as read
$PY -m scripts.related_work.papers todo                  # what is unread
```

The index is currently built over the whole `Literature/` tree, not just
`Zpapers/` — see "The corpus is wider than Zpapers" in `review.md`.

## Conventions

- **`review.md` distinguishes read from title-triaged.** Do not promote a paper
  to "read" without reading it. The distinction is the point of the file.
- **Counts come from `data/reading_log.csv`**, never from prose. Two counts
  written into `review.md` were wrong before the log existed.
- **Record matches you cannot verify as `weak`,** not as absent and not as
  found. `match_refs.py` labels a surname-and-year-only match `weak` because
  filenames truncate titles; those need an eye.
- **Paths in `data/` are relative to the `Literature/` corpus root**, so the index survives being shared.

## Open

`review.md` ends with what has not been ingested: 340 of 385 papers are
title-triaged only. The obvious next tranche is the data-quality and cleaning
cluster, since that is the application side of the bridge.