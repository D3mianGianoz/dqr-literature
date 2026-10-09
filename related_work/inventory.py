"""Inventory the local paper collection for the related-work review.

Walks a literature root, parses year and title from each filename,
and writes a CSV index. Re-runnable as the collection grows.

Usage:
    uv run python -m related_work.inventory
"""

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from related_work.config import CORRECTIONS, INVENTORY, corpus_root

YEAR = re.compile(r"\b(19|20)\d{2}\b")


def parse(paper: Path) -> tuple[str, str, str]:
    """Return (year, author, title) parsed from the filename.

    The author segment must be kept: dropping it makes titles ambiguous and
    breaks matching against bibliographies.
    """
    stem = paper.stem.replace("_", " ").replace("-", " ")
    match = YEAR.search(stem)
    if match:
        return (
            match.group(0),
            stem[: match.start()].strip(),
            stem[match.end() :].strip(),
        )
    folder = paper.parent.name
    return (folder if YEAR.fullmatch(folder) else ""), "", stem


def _title_key(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).casefold()
    return " ".join(
        "".join(char if char.isalnum() else " " for char in normalized).split()
    )


def load_overrides() -> dict[str, dict[str, str]]:
    """Load metadata overrides from the corrections file."""
    if not CORRECTIONS.exists():
        return {}
    try:
        with CORRECTIONS.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, IOError) as exc:
        print(f"Warning: could not load overrides: {exc}")
        return {}


def apply_overrides(rows: list[dict[str, str]], overrides: dict[str, dict[str, str]]) -> None:
    """Apply overrides to rows based on the paper path."""
    for row in rows:
        if path := row.get("path"):
            if override := overrides.get(path):
                row.update(override)


def enrich(
    rows: list[dict[str, str]], items: list[dict]
) -> tuple[list[dict[str, str]], int, int]:
    records = {}
    attachments: dict[str, set[str]] = defaultdict(set)
    for item in items:
        data = item.get("data", {})
        key = data.get("key")
        if not key:
            continue
        if data.get("parentItem"):
            filename = data.get("filename") or data.get("path", "")
            if (
                data.get("contentType", "").lower() == "application/pdf"
                or filename.lower().endswith(".pdf")
            ):
                if filename:
                    attachments[data["parentItem"]].add(
                        Path(filename.replace("\\", "/")).name
                    )
        elif data.get("itemType") not in {"attachment", "note", "annotation"}:
            records[key] = data

    by_filename: dict[str, set[str]] = defaultdict(set)
    by_title: dict[str, set[str]] = defaultdict(set)
    for key, data in records.items():
        title = _title_key(data.get("title", ""))
        if title:
            by_title[title].add(key)
        for filename in attachments[key]:
            if filename:
                by_filename[Path(filename).name.casefold()].add(key)

    rows_by_filename: dict[str, set[int]] = defaultdict(set)
    for index, row in enumerate(rows):
        rows_by_filename[Path(row["path"]).name.casefold()].add(index)

    candidates = [set() for _ in rows]
    for filename, keys in by_filename.items():
        for index in rows_by_filename[filename]:
            candidates[index].update(keys)
    for index, row in enumerate(rows):
        candidates[index].update(by_title.get(_title_key(row["title"]), set()))
        if row["year"]:
            candidates[index] = {
                key
                for key in candidates[index]
                if not (year := YEAR.search(records[key].get("date", "")))
                or row["year"] == year.group()
            }

    references = Counter(key for matches in candidates for key in matches)
    enriched = []
    ambiguous = 0
    for row, matches in zip(rows, candidates):
        updated = {**row, "zotero_key": "", "abstract": ""}
        if len(matches) == 1:
            key = next(iter(matches))
            if references[key] == 1:
                data = records[key]
                authors = [
                    creator.get("name")
                    or " ".join(
                        part
                        for part in (
                            creator.get("firstName", ""),
                            creator.get("lastName", ""),
                        )
                        if part
                    )
                    for creator in data.get("creators", [])
                    if creator.get("creatorType") == "author"
                ]
                year = YEAR.search(data.get("date", ""))
                updated.update(
                    year=year.group() if year else row["year"],
                    author=" and ".join(authors) or row["author"],
                    title=data.get("title") or row["title"],
                    zotero_key=key,
                    abstract=data.get("abstractNote", ""),
                )
            else:
                ambiguous += 1
        elif matches:
            ambiguous += 1
        enriched.append(updated)
    return enriched, sum(bool(row["zotero_key"]) for row in enriched), ambiguous


def _zotero_items() -> list[dict]:
    try:
        from pyzotero import Zotero
    except ImportError as exc:
        raise SystemExit(
            "Install Zotero support with "
            "`uv sync --extra zotero`."
        ) from exc
    zotero = Zotero("0", "user", local=True)
    return zotero.everything(zotero.items())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, help="literature root (defaults to [tool.dqr-literature].lit_root in pyproject.toml)")
    ap.add_argument("--out", type=Path, help="CSV output path")
    ap.add_argument(
        "--zotero-local",
        action="store_true",
        help="enrich the PDF inventory from the running local Zotero library",
    )
    args = ap.parse_args()
    root = corpus_root(args.root)
    out = args.out or INVENTORY

    overrides = load_overrides()

    rows = []
    for paper in sorted(root.rglob("*.pdf")):
        year, author, title = parse(paper)
        rows.append(
            {
                "year": year,
                "author": author,
                "title": title,
                "path": str(paper.relative_to(root)),
            }
        )
    matched = 0
    if args.zotero_local:
        rows, matched, ambiguous = enrich(rows, _zotero_items())
    elif out.resolve() == INVENTORY.resolve() and out.exists():
        with out.open(encoding="utf-8", newline="") as fh:
            previous = {row["path"]: row for row in csv.DictReader(fh)}
        for row in rows:
            old = previous.get(row["path"], {})
            if old.get("zotero_key"):
                row.update(
                    {
                        field: old.get(field, row.get(field, ""))
                        for field in ("year", "author", "title", "zotero_key", "abstract")
                    }
                )

    apply_overrides(rows, overrides)

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        fields = ["year", "author", "title", "path", "zotero_key", "abstract"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(out)

    message = f"{len(rows)} papers -> {out}"
    if args.zotero_local:
        unmatched = len(rows) - matched - ambiguous
        message += (
            f" ({matched} matched, {ambiguous} ambiguous, {unmatched} unmatched)"
        )
    print(message)


if __name__ == "__main__":
    main()
