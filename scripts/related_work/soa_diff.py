#!/usr/bin/env python3
"""Reproduce the SoTA bibliography diff: every row of data/soa_citations.csv
with local=yes is matched against data/inventory.csv and compared to the
expected method/path recorded in the CSV.

Usage: python scripts/related_work/soa_diff.py
"""

import csv
from pathlib import Path

from scripts.related_work.match_refs import match

REPO = Path(__file__).resolve().parent.parent.parent
INVENTORY = REPO / "data" / "inventory.csv"
SOA = REPO / "data" / "soa_citations.csv"


def main() -> int:
    rows = list(csv.DictReader(INVENTORY.open(encoding="utf-8")))
    promoted: list[tuple[str, str, str]] = []
    regressions: list[tuple[str, str, str]] = []
    missing: list[tuple[str, str, str]] = []

    for row in csv.DictReader(SOA.open(encoding="utf-8")):
        if row["local"] != "yes":
            continue
        entry = (row["year"], row["surnames"].split("|"), row["citation"])
        best_row, method = match(entry, rows)
        if best_row is None:
            if method == "none" and row["method"] != "none":
                regressions.append((row["ref"], row["method"], method))
            if method != "none" and row["method"] == "none":
                missing.append((row["ref"], row["method"], method))
        else:
            if best_row.get("path", "") != row["local_path"]:
                promoted.append((row["ref"], row["method"], method))
            if method == "none" and row["method"] != "none":
                regressions.append((row["ref"], row["method"], method))
            if method != "none" and row["method"] == "none":
                missing.append((row["ref"], row["method"], method))

    print("promotions:", promoted)
    print("regressions:", regressions)
    print("missing:", missing)
    return 0 if not (promoted or regressions or missing) else 1


if __name__ == "__main__":
    raise SystemExit(main())