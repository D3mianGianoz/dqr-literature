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
        # Split on ". " only when not preceded by a capital, so "Richard Y. Wang"
        # keeps its surname instead of being cut at the initial.
        head = re.split(r"(?<![A-Z])\.\s+", body)[0]
        sur = []
        for chunk in re.split(r",| and ", head):
            toks = [t for t in chunk.replace(".", " ").split() if len(t) > 1]
            if toks and toks[0][:1].isupper():
                sur.append(toks[-1].lower())
        found[parts[i]] = (years[-1] if years else "", sur, body)
    return found


def title_tokens(citation: str) -> set[str]:
    """Distinctive words from the title segment of a bibliographic entry."""
    stop = set(
        "the and for with from that this into using based between over under "
        "their have been will more than data method approach".split()
    )
    words: set[str] = set()
    for seg in re.split(r"\.\s+", citation)[1:]:
        if YEAR.search(seg) or "," in seg[:12]:  # reached the journal/venue
            break
        words |= {w for w in re.findall(r"[a-z]{4,}", seg.lower()) if w not in stop}
    return words or {w for w in re.findall(r"[a-z]{5,}", citation.lower()) if w not in stop}


def match(row: tuple[str, list[str], str], rows: list[dict[str, str]]) -> tuple[dict[str, str] | None, str]:
    """Return (row, method). Exact surname+year first, then a guarded fuzzy pass."""
    year, sur, citation = row
    for r in rows:
        if r["year"] == year and any(s in (r["author"] + r["title"]).lower() for s in sur):
            return r, "exact"

    # Fuzzy: same surname family but the year differs, or a short/obscure
    # citation whose title is distinctive enough. Requiring the surname stops
    # "Deep Learning" from matching any paper that merely uses deep learning.
    words = title_tokens(citation)
    best, best_score = None, 0.0
    for r in rows:
        blob = (r["author"] + " " + r["title"]).lower()
        overlap = sum(1 for w in words if w in blob) / max(len(words), 1)
        same_author = any(s[:5] in (r["author"] + r["title"]).lower() for s in sur)
        year_ok = abs(int(r["year"] or 0) - int(year or 0)) <= 1 if year else False
        if overlap >= 0.85 and (same_author or year_ok) and overlap > best_score:
            best, best_score = r, overlap
    if best is None:
        return None, "none"
    return best, f"fuzzy:{best_score:.2f}"


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
    exact = sum(r["method"] == "exact" for r in out)
    fuzzy = sum(r["method"].startswith("fuzzy") for r in out)
    absent = sum(r["local"] == "no" for r in out)
    print(
        f"{exact + fuzzy}/{len(out)} available ({exact} exact, {fuzzy} fuzzy,"
        f" {absent} absent) -> {args.out}"
    )


if __name__ == "__main__":
    main()