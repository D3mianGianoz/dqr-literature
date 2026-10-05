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
# ". " that is *not* preceded by a capital, so "Richard Y. Wang" survives.
SENTENCE = re.compile(r"(?<![A-Z])\.\s+")


def entries(text: str) -> dict[str, tuple[str, list[str], str]]:
    """Return {ref: (year, surnames, citation)} for a numbered bibliography."""
    parts = ENTRY.split(text.split("Bibliography", 1)[-1])
    found: dict[str, tuple[str, list[str], str]] = {}
    for i in range(1, len(parts), 2):
        body = re.sub(r"\s+", " ", PAGE_FOOTER.sub(" ", parts[i + 1])).strip()
        years = YEAR.findall(body)
        # Split on ". " only when not preceded by a capital, so "Richard Y. Wang"
        # keeps its surname instead of being cut at the initial.
        head = SENTENCE.split(body)[0]
        sur = []
        for chunk in re.split(r",| and ", head):
            toks = [t for t in chunk.replace(".", " ").split() if len(t) > 1]
            if toks and toks[0][:1].isupper():
                sur.append(toks[-1].lower())
        found[parts[i]] = (years[-1] if years else "", sur, body)
    return found


def title_tokens(citation: str) -> set[str]:
    """Distinctive words from the title segment of a bibliographic entry.

    The title is the first segment after the author list. Scanning forward
    instead runs into author surnames and the publisher line, which drags the
    overlap score down and makes real matches look wrong.
    """
    stop = set(
        "the and for with from that this into using based between over under "
        "their have been will more than data method approach".split()
    )
    segments = SENTENCE.split(citation)
    title = segments[1] if len(segments) > 1 else citation
    return {w for w in re.findall(r"[a-z]{4,}", title.lower()) if w not in stop}


def match(
    row: tuple[str, list[str], str], rows: list[dict[str, str]]
) -> tuple[dict[str, str] | None, str]:
    """Return (row, method).

    The primary author must match, the year must match, and either the titles
    must overlap or the file must carry more than one author surname. Matching on
    any surname alone is unsafe: "Wang & Strong" (1996) otherwise matches "Wand &
    Wang" (1996) on surname and year, which coincide by accident.
    """
    year, sur, citation = row
    words = title_tokens(citation)
    best, best_score, best_method = None, 0.0, "none"
    for r in rows:
        blob = (r["author"] + " " + r["title"]).lower()
        if not sur or sur[0] not in blob or r["year"] != year:
            continue
        overlap = sum(1 for w in words if w in blob) / max(len(words), 1)
        # filenames often truncate author lists to "X et al", so a second
        # surname only counts as corroboration, never as a requirement
        corroboration = sum(1 for s in sur if s in blob) >= 2
        if overlap >= 0.5:
            score = 1.0
        elif corroboration:
            score = 0.8
        elif len(words) <= 2 or overlap < 0.25:
            # short or uninformative filename ("NFAD.pdf"): surname and year
            # agree but the title cannot corroborate. Real, but needs a human.
            score = 0.3
        else:
            continue
        if score > best_score:
            best, best_score = r, score
            best_method = {1.0: "exact", 0.8: "exact:cited", 0.3: "weak"}[score]
    return best, best_method


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refs", type=Path, required=True, help="dumped bibliography text")
    ap.add_argument("--inventory", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rows = list(csv.DictReader(args.inventory.open(encoding="utf-8")))
    out = []
    for ref, parsed in entries(args.refs.read_text(encoding="utf-8")).items():
        hit, method = match(parsed, rows)
        out.append(
            {
                "ref": ref,
                "year": parsed[0],
                "surnames": "|".join(parsed[1][:3]),
                "local": "yes" if hit else "no",
                "method": method,
                "local_path": hit["path"] if hit else "",
                "citation": parsed[2][:300],
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    exact = sum(r["method"].startswith("exact") for r in out)
    weak = sum(r["method"] == "weak" for r in out)
    absent = sum(r["local"] == "no" for r in out)
    print(
        f"{exact + weak}/{len(out)} found ({exact} strong, {weak} weak needing"
        f" confirmation, {absent} absent) -> {args.out}"
    )


if __name__ == "__main__":
    main()
