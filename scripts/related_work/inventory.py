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
YEAR_DIR = re.compile(r"(19|20)\d{2}")

# Themes that matter for the blind-detection study: whether existing anomaly
# detection methods are fit for automated sensor-data cleaning.
THEMES: dict[str, str] = {
    "metrics": r"metric|evaluat|accuracy measure|scoring|\bvus\b|segmentation",
    "benchmark": r"benchmark|rethink|comparab|real.world|real world",
    "fault_diagnosis": r"fault detect|fault diagnos|fault classif|sensor fault|fault local",
    "data_quality": r"data quality|data clean|outlier|imput|corrupt|noise removal",
    "time_series_ad": r"time.series|anomaly detect|outlier detect|univariate|multivariate",
    "drift": r"drift|contaminat|concept change",
    "model_selection": r"model selection|hyperparam|ensemble|base learner",
    "explainability": r"explainab|interpret|explanation",
    "shm": r"structural health|\bshm\b|infrastructure|bridge|civil",
    "injection": r"injection|synthetic|simulat.*fault",
}


def parse(paper: Path, root: Path) -> tuple[str, str]:
    """Return (year, title) parsed from the filename, falling back to the folder."""
    stem = paper.stem.replace("_", " ").replace("-", " ")
    match = YEAR.search(stem)
    if match:
        return match.group(0), stem[match.end() :].strip()
    folder = paper.parent.name
    return (folder if YEAR_DIR.fullmatch(folder) else ""), stem


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True, help="literature root")
    ap.add_argument("--out", type=Path, required=True, help="CSV output path")
    args = ap.parse_args()

    rows = []
    for paper in sorted(args.root.rglob("*.pdf")):
        year, title = parse(paper, args.root)
        tags = sorted(t for t, pat in THEMES.items() if re.search(pat, title, re.I))
        rows.append(
            {
                "year": year,
                "title": title,
                "themes": "|".join(tags),
                "path": str(paper),
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["year", "title", "themes", "path"])
        writer.writeheader()
        writer.writerows(rows)

    untagged = sum(1 for r in rows if not r["themes"])
    print(f"{len(rows)} papers -> {args.out} ({untagged} untagged by filename)")


if __name__ == "__main__":
    main()