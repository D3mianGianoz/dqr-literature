"""Match a thesis/paper bibliography against the local collection.

Reads a bibliography dumped to text (e.g. `pdftotext thesis.pdf -`), extracts
numbered entries, and reports which have a local PDF.

Matching is by *surname* plus year. Matching on first names, or on the
inventory title alone, silently misses everything: bibliographic entries lead
with given names and the inventory drops the author segment from the title.

Usage:
    pdftotext paper.pdf /tmp/refs.txt
    python -m scripts.related_work.match_refs --refs /tmp/refs.txt \\
        --inventory data/inventory.csv --out data/soa_citations.csv
"""

import argparse
import csv
import re
from pathlib import Path

ENTRY = re.compile(r"\n\[(\d+)\]\s*")
YEAR = re.compile(r"\b((?:19|20)\d{2})\b")
PAGE_FOOTER = re.compile(r"USES2.*?\d+\s*")


def entries(text: str) -> dict[str, tuple[str, list[str], str]]:
    """Return {ref: (year, surnames, citation)} for a numbered bibliography."""
    parts = ENTRY.split(text.split("Bibliography", 1)[-1])
    found: dict[str, tuple[str, list[str], str]] = {}
    for i in range(1, len(parts), 2):
        body = re.sub(r"\s+", " ", PAGE_FOOTER.sub(" ", parts[i + 1])).strip()
        years = YEAR.findall(body)
        head = body.split(". ")[0]
        sur = []
        for chunk in re.split(r",| and ", head):
            toks = [t for t in chunk.replace(".", " ").split() if len(t) > 1]
            if toks and toks[0][:1].isupper():
                sur.append(toks[-1].lower())
        found[parts[i]] = (years[-1] if years else "", sur, body)
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refs", type=Path, required=True, help="dumped bibliography text")
    ap.add_argument("--inventory", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rows = list(csv.DictReader(args.inventory.open(encoding="utf-8")))
    out = []
    for ref, (year, sur, cite) in entries(args.refs.read_text(encoding="utf-8")).items():
        hit = next(
            (
                r
                for r in rows
                if r["year"] == year
                and any(s in (r["author"] + r["title"]).lower() for s in sur)
            ),
            None,
        )
        out.append(
            {
                "ref": ref,
                "year": year,
                "surnames": "|".join(sur[:3]),
                "local": "yes" if hit else "no",
                "local_path": hit["path"] if hit else "",
                "citation": cite[:300],
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{sum(r['local'] == 'yes' for r in out)}/{len(out)} citations available locally -> {args.out}")


if __name__ == "__main__":
    main()