"""Inventory the local paper collection for the related-work review.

Walks a literature root, parses year and title from each filename, tags themes,
and writes a CSV index. Re-runnable as the collection grows.

Usage:
    python -m scripts.related_work.inventory --root <lit-root> --out <csv>
"""

import argparse
import csv
import re
from pathlib import Path

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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True, help="literature root")
    ap.add_argument("--out", type=Path, required=True, help="CSV output path")
    args = ap.parse_args()

    rows = []
    for paper in sorted(args.root.rglob("*.pdf")):
        year, author, title = parse(paper)
        rows.append(
            {
                "year": year,
                "author": author,
                "title": title,
                "path": str(paper),
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["year", "author", "title", "path"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} papers -> {args.out}")


if __name__ == "__main__":
    main()
