#!/usr/bin/env python3
"""Reproduce the SoTA bibliography diff: every row of data/soa_citations.csv
with local=yes is matched against data/inventory.csv and compared to the
expected method/path recorded in the CSV.

Usage: uv run python -m related_work.soa_diff
"""

import csv

from related_work.config import INVENTORY, SOA, inventory_path
from related_work.match_refs import match


def main() -> int:
    with INVENTORY.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    with SOA.open(encoding="utf-8") as fh:
        soa_rows = list(csv.DictReader(fh))

    path_diffs: list[tuple[str, str, str]] = []
    regressions: list[tuple[str, str, str]] = []

    for row in soa_rows:
        if row["local"] != "yes":
            continue
        entry = (row["year"], row["surnames"].split("|"), row["citation"])
        best_row, method = match(entry, rows)
        if best_row is None:
            regressions.append((row["ref"], row["method"], "none"))
        else:
            expected_path = inventory_path(row["local_path"])
            matched_path = best_row.get("path", "")
            if matched_path != expected_path:
                path_diffs.append((row["ref"], expected_path, matched_path))

    print("path diffs:", path_diffs)
    print("regressions:", regressions)
    return 0 if not (path_diffs or regressions) else 1


if __name__ == "__main__":
    raise SystemExit(main())