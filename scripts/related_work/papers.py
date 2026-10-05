"""Read and track papers in the local collection.

Compact abstract extraction, plus a machine-checkable reading log so read/unread
counts stop being tracked in prose (they have been wrong twice).

Usage:
    python -m scripts.related_work.papers show "metric maze"   # compact abstract
    python -m scripts.related_work.papers show --ref 20         # by SoTA ref number
    python -m scripts.related_work.papers mark "metric maze"   # record as read
    python -m scripts.related_work.papers todo                  # what is unread
"""

import argparse
import csv
import re
import subprocess
import textwrap
from pathlib import Path

DOCS = Path("data")
INVENTORY = DOCS / "inventory.csv"
SOA = DOCS / "soa_citations.csv"
LOG = DOCS / "reading_log.csv"


def _load(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8"))) if path.exists() else []


def find(query: str | None, ref: str | None) -> tuple[dict[str, str], str | None]:
    """Return (row, source) for a query over the SoTA citations then the inventory."""
    if ref:
        for r in _load(SOA):
            if r["ref"] == ref and r["local"] == "yes":
                return {
                    "path": r["local_path"],
                    "citation": r["citation"],
                    "year": r["year"],
                }, "soa"
    for r in _load(SOA):  # a SoTA citation is more specific than a collection entry
        if r["local"] == "yes" and query and query.lower() in r["surnames"].lower():
            return {
                "path": r["local_path"],
                "citation": r["citation"],
                "year": r["year"],
            }, "soa"
    for r in _load(INVENTORY):
        if query and (
            query.lower() in r["author"].lower() or query.lower() in r["title"].lower()
        ):
            return r, "inv"
    raise SystemExit(f"no match for {query or ref!r}")


def _log() -> list[dict[str, str]]:
    return _load(LOG)


def show(query: str | None, ref: str | None, chars: int) -> None:
    row, source = find(query, ref)
    text = subprocess.run(
        ["pdftotext", row["path"], "-"], capture_output=True, text=True
    ).stdout
    flat = re.sub(r"\s+", " ", text)
    # "abstract" also occurs mid-document ("abstracting heterogeneity"), so only
    # trust it near the front; otherwise take the document opening.
    at = flat.lower().find("abstract")
    if at < 0 or at > 0.15 * len(flat):
        at = 0
    body = flat[at : at + chars]
    name = Path(row["path"]).stem
    print(f"### {name} [{source}] {row.get('year', '')}")
    print(textwrap.fill(body, 100))


def mark(query: str | None, ref: str | None) -> None:
    row, source = find(query, ref)
    entries = _log()
    key = Path(row["path"]).stem
    if any(e["key"] == key for e in entries):
        print(f"already logged: {key}")
        return
    entries.append(
        {
            "key": key,
            "source": source,
            "year": row.get("year", ""),
            "soa_ref": ref or "",
            "citation": row.get("citation", "")[:200],
        }
    )
    with LOG.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["key", "source", "year", "soa_ref", "citation"]
        )
        w.writeheader()
        w.writerows(sorted(entries, key=lambda e: (e["source"], e["key"])))
    print(f"logged: {key}  ({len(entries)} read)")


def todo() -> None:
    entries = _log()
    read = {e["key"] for e in entries}
    soa = [r for r in _load(SOA) if r["local"] == "yes"]
    inv = _load(INVENTORY)
    soa_unread = [r for r in soa if Path(r["local_path"]).stem not in read]
    inv_unread = [r for r in inv if Path(r["path"]).stem not in read]
    print(
        f"read: {len(read)}   SoTA local {len(soa)} ({len(soa_unread)} unread)"
        f"   collection {len(inv)} ({len(inv_unread)} unread)"
    )
    print("\nunread SoTA references, in bibliography order:")
    for r in soa_unread:
        print(f"  [{r['ref']:>2}] {r['year']} {r['surnames']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("show", "mark"):
        c = sub.add_parser(cmd)
        c.add_argument("query", nargs="?")
        c.add_argument("--ref")
        if cmd == "show":
            c.add_argument("--chars", type=int, default=1400)
    sub.add_parser("todo")
    a = ap.parse_args()
    {
        "show": lambda: show(a.query, a.ref, a.chars),
        "mark": lambda: mark(a.query, a.ref),
        "todo": todo,
    }[a.cmd]()


if __name__ == "__main__":
    main()
