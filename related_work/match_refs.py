"""Match a thesis/paper bibliography against the local collection.

Reads a bibliography dumped to text (e.g. `pdftotext thesis.pdf -`), extracts
numbered entries, and reports which have a local PDF.

Matching is by *surname* plus year. Matching on first names, or on the
inventory title alone, silently misses everything: bibliographic entries lead
with given names and the inventory drops the author segment from the title.

A dense (word2vec-style) title similarity is computed on top of the lexical
overlap so that an exact-title match is detected even when the filename
truncates the bibliographic citation.

Usage:
    pdftotext paper.pdf /tmp/refs.txt
    uv run python -m related_work.match_refs --refs /tmp/refs.txt
"""

import argparse
import csv
import re
from pathlib import Path

import spacy

from related_work.config import INVENTORY, SOA

ENTRY = re.compile(r"\n\[(\d+)\]\s*")
YEAR = re.compile(r"\b((?:19|20)\d{2})\b")
PAGE_FOOTER = re.compile(r"USES2.*?\d+\s*")
# ". " that is *not* preceded by a capital, so "Richard Y. Wang" survives.
SENTENCE = re.compile(r"(?<![A-Z])\.\s+")
RANK = {"exact": 2, "exact:cited": 1, "weak": 0}

# en_core_web_md is the sole user's model: load it once at import time.
# No fallback path — a missing model is a hard failure (sole user).
nlp = spacy.load("en_core_web_md")


def _surname_regex(head: str) -> list[str]:
    """Fallback surname extraction from an author segment using plain regex.

    ``head`` is the text before the first sentence-ending ". " (e.g.
    "Richard Y. Wang and Diane M. Strong").
    """
    sur = []
    for chunk in re.split(r",| and ", head):
        toks = [t for t in chunk.replace(".", " ").split() if len(t) > 1]
        if toks and toks[0][:1].isupper():
            sur.append(toks[-1].lower())
    return sur


def _surname_ner(head: str) -> list[str]:
    """Surname extraction via spaCy PERSON entities, per author chunk.

    NER is run per author segment (split on ", " / " and ") to catch the first
    author in a comma list (e.g. "Guansong Pang") and to preserve multi-word
    surnames ("Anton Van Den Hengel", "Bertrand-Krajewski"). We only accept an
    entity whose span reaches the end of its chunk; a partial span (e.g. "Matias
    Carrasco" without "Kind") is ignored and that chunk falls back to the regex
    extractor, which handles initials like "T. Lewis" correctly.
    """
    sur: list[str] = []
    for chunk in re.split(r",| and ", head):
        chunk = chunk.strip()
        if not chunk:
            continue
        doc = nlp(chunk)
        last_ent = None
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                last_ent = ent
        if last_ent is not None and last_ent.end_char == len(chunk):
            toks = [t for t in last_ent.text.split() if len(t) > 1]
            if toks:
                sur.append(toks[-1].lower())
                continue
        # regex fallback for this chunk: initials ("T. Lewis") and names NER
        # did not tag at all
        sur += _surname_regex(chunk)
    return sur


def entries(text: str) -> dict[str, tuple[str, list[str], str]]:
    """Return {ref: (year, surnames, citation)} for a numbered bibliography."""
    parts = ENTRY.split(text.split("Bibliography", 1)[-1])
    found: dict[str, tuple[str, list[str], str]] = {}
    for i in range(1, len(parts), 2):
        body = re.sub(r"\s+", " ", PAGE_FOOTER.sub(" ", parts[i + 1])).strip()
        years = YEAR.findall(body)
        head = SENTENCE.split(body)[0]
        # SpaCy NER is the primary surname extractor; regex fallback only when
        # NER found no PERSON entities at all.
        sur = _surname_ner(head) or _surname_regex(head)
        found[parts[i]] = (years[-1] if years else "", sur, body)
    return found


def _title_segment(citation: str) -> str:
    """The title is the first sentence after the author list."""
    segments = SENTENCE.split(citation)
    return segments[1] if len(segments) > 1 else citation


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
    title = _title_segment(citation)
    return {w for w in re.findall(r"[a-z]{4,}", title.lower()) if w not in stop}


def match(
    entry: tuple[str, list[str], str], rows: list[dict[str, str]]
) -> tuple[dict[str, str] | None, str]:
    """Return (row, method).

    The primary author must match, the year must match, and either the titles
    must overlap or the file must carry more than one author surname. Matching on
    any surname alone is unsafe: "Wang & Strong" (1996) otherwise matches "Wand &
    Wang" (1996) on surname and year, which coincide by accident.

    A dense (word2vec-style) title similarity complements the lexical overlap:
    an exact title match is scored as "exact" even when the filename truncates
    the citation, and "exact:cited" for a strongly related title.
    """
    year, sur, citation = entry
    words = title_tokens(citation)
    best, best_method, best_rank = None, "none", -1
    for r in rows:
        blob = (r["author"] + " " + r["title"]).lower()
        if not sur or sur[0] not in blob or r["year"] != year:
            continue
        # title segment vs inventory title, both lowercased so case cannot
        # defeat the dense matcher. NER/tagger/etc. are disabled: we only need
        # vectors.
        cited_title = _title_segment(citation).lower()
        # empty inventory titles give empty vectors -> [W008] warning; treat
        # them as no similarity match rather than spamming the log
        inv_title = r["title"].lower()
        similarity = (
            nlp(cited_title).similarity(nlp(inv_title))
            if inv_title.strip() and nlp(inv_title).vector.sum()
            else 0.0
        )
        overlap = sum(1 for w in words if w in blob) / max(len(words), 1)
        # filenames often truncate author lists to "X et al", so a second
        # surname only counts as corroboration, never as a requirement
        corroboration = sum(1 for s in sur if s in blob) >= 2
        # combine lexical overlap with dense title similarity: similarity alone
        # is too topic-general on the md word2vec model (two different "data
        # quality" papers score 0.8+), so a lexical guard is required.
        if overlap >= 0.5:
            method = "exact"
        elif similarity >= 0.5 and overlap >= 0.2:
            method = "exact"
        elif corroboration or similarity >= 0.25 and overlap >= 0.2:
            method = "exact:cited"
        elif len(words) <= 2 or overlap < 0.25:
            # short or uninformative filename ("NFAD.pdf"): surname and year
            # agree but the title cannot corroborate. Real, but needs a human.
            method = "weak"
        else:
            continue
        if RANK[method] > best_rank:
            best, best_method, best_rank = r, method, RANK[method]
    return best, best_method


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refs", type=Path, required=True, help="dumped bibliography text")
    ap.add_argument("--inventory", type=Path, default=INVENTORY)
    ap.add_argument("--out", type=Path, default=SOA)
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
