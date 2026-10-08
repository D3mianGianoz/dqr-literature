"""Read and track papers in the local collection.

Compact abstract extraction, plus a machine-checkable reading log so read/unread
counts stop being tracked in prose (they have been wrong twice).

Usage:
    uv run python -m related_work.papers show "metric maze"
    uv run python -m related_work.papers show --ref 20
    uv run python -m related_work.papers mark "metric maze"
    uv run python -m related_work.papers todo
"""

import argparse
import csv
import re
import subprocess
import textwrap
from collections import Counter
from pathlib import Path

import spacy

from related_work.config import (
    INVENTORY,
    READING_LOG as LOG,
    SOA,
    corpus_root,
    inventory_path,
)

nlp = spacy.load("en_core_web_md")


def _load(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8"))) if path.exists() else []


def _norm_text(s: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFKC", s).casefold()


def find(query: str | None, ref: str | None) -> tuple[dict[str, str], str]:
    """Return (row, source) for a query over the SoTA citations then the inventory."""
    q_norm = _norm_text(query) if query else ""
    soa = [
        r
        for r in _load(SOA)
        if r["local"] == "yes"
        and (r["ref"] == ref if ref else q_norm in _norm_text(r["surnames"]))
    ]
    if soa:
        r = soa[0]
        inv_p = inventory_path(r["local_path"])
        inv_match = next((row for row in _load(INVENTORY) if row.get("path") == inv_p), {})
        return (
            {
                "path": inv_p,
                "citation": r["citation"],
                "year": r["year"],
                "zotero_key": inv_match.get("zotero_key", ""),
                "author": inv_match.get("author", ""),
                "title": inv_match.get("title", ""),
            },
            "soa",
        )
    for r in _load(INVENTORY):
        if query and (
            q_norm in _norm_text(r["author"]) or q_norm in _norm_text(r["title"])
        ):
            return r, "inv"
    raise SystemExit(f"no match for {query or ref!r}")


def _extract_abstract(sentences: list[str]) -> list[str]:
    """Return the abstract sentences, or [] if none found.

    Finds the sentence containing "abstract" (case-insensitive) near the front
    of the document and collects the following sentences until a section
    heading (an "Introduction"-style line) appears.
    """
    if not sentences:
        return []
    half = max(1, len(sentences) // 2)
    abstract_idx = None
    for i in range(half):
        if "abstract" in sentences[i].lower():
            abstract_idx = i
            break
    if abstract_idx is None:
        return []
    # skip a bare "abstract" heading
    start = abstract_idx + 1 if sentences[abstract_idx].strip().lower() == "abstract" else abstract_idx
    abstract = []
    for sent in sentences[start:]:
        low = sent.strip().lower()
        # stop at the first section heading ("Introduction", "1 Introduction",
        # "Introduction: Background ...")
        if re.match(r"^\d*(?:\.\d+)?\s*introduction\b", low):
            break
        abstract.append(sent)
    return abstract


def _rank_sentences(doc: spacy.tokens.Doc, alpha: float = 0.4, beta: float = 0.6) -> list[int]:
    """Rank sentences by position weight + term frequency.

    Position weight favours earlier sentences (abstracts/front matter); term
    frequency favours sentences whose words recur in the document. Returns
    sentence indices, best first.
    """
    sentences = list(doc.sents)
    n = len(sentences)
    if n == 0:
        return []
    word_freq = Counter(w.text.lower() for w in doc if w.is_alpha and not w.is_stop)
    max_freq = max(word_freq.values()) if word_freq else 1
    scores = []
    for i, s in enumerate(sentences):
        s_words = [w.text.lower() for w in s if w.is_alpha and not w.is_stop]
        if s_words:
            tf = sum(word_freq.get(w, 0) for w in s_words) / (len(s_words) * max_freq)
        else:
            tf = 0.0
        pos = 1.0 / (i + 1)
        scores.append(alpha * pos + beta * tf)
    return sorted(range(n), key=lambda i: scores[i], reverse=True)


def _extractive_summary(doc: spacy.tokens.Doc, k: int = 3) -> list[str]:
    """Top-k sentences by position weight + term frequency, in document order."""
    order = _rank_sentences(doc)
    chosen = sorted(order[:k])
    sentences = list(doc.sents)
    return [sentences[i].text.strip() for i in chosen]


def show(
    query: str | None, ref: str | None, chars: int, root: Path = Path(".")
) -> None:
    row, source = find(query, ref)
    pdf = Path(row["path"])
    if not pdf.is_absolute():
        pdf = root / pdf
    text = subprocess.run(
        ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    flat = re.sub(r"\s+", " ", text)
    doc = nlp(flat)
    sentences = [s.text.strip() for s in doc.sents]
    abstract = _extract_abstract(sentences)
    if abstract:
        body = " ".join(abstract)
    else:
        # no labelled abstract: fall back to an extractive summary
        body = " ".join(_extractive_summary(doc, 3))
    body = body[:chars]
    name = Path(row["path"]).stem
    print(f"### {name} [{source}] {row.get('year', '')}")
    print(textwrap.fill(body, 100))


def mark(query: str | None, ref: str | None) -> None:
    row, source = find(query, ref)
    entries = _load(LOG)
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
    entries = _load(LOG)
    read = {e["key"] for e in entries}
    soa = [r for r in _load(SOA) if r["local"] == "yes"]
    inv = _load(INVENTORY)
    soa_unread = [r for r in soa if Path(r["local_path"]).stem not in read]
    inv_unread = [r for r in inv if Path(r["path"]).stem not in read]
    print(f"Logged as read: {len(read)} papers")
    print(
        f"Local SoTA references: {len(soa)} total, "
        f"{len(soa_unread)} unread"
    )
    print(
        f"Full inventory: {len(inv)} total, "
        f"{len(inv_unread)} unread"
    )
    print("\nUnread local SoTA references, in bibliography order:")
    if soa_unread:
        for r in soa_unread:
            print(f"  [{r['ref']:>2}] {r['year']} {r['surnames']}")
    else:
        print("  none")


def recommend(query: str, unread_only: bool = True, limit: int = 10) -> None:
    from related_work.semantic import rank_inventory

    results = rank_inventory(query, unread_only=unread_only, top_k=limit)
    if not results:
        print(f"no papers found for query: {query!r}")
        return

    status = "unread" if unread_only else "all"
    print(f"Top {len(results)} recommendations ({status}) for: {query!r}\n")
    for r in results:
        read_badge = "[read]  " if r["is_read"] else "[unread]"
        score_pct = f"{r['score']:.1%}"
        print(f"  {score_pct:>5} {read_badge} ({r['year'] or '----'}) {r['author']} — {r['title']}")
        print(f"         path: {r['path']}")
        if r.get("zotero_key"):
            print(f"         zotero: {r['zotero_key']}")
        print()


def annotations(query: str | None, ref: str | None) -> None:
    from related_work.zotero import ZoteroClient

    row, source = find(query, ref)
    key = row.get("zotero_key")
    stem = Path(row["path"]).stem

    client = ZoteroClient()
    if not client.is_available():
        raise SystemExit("Zotero local API is not running. Start Zotero to fetch annotations.")

    # Resolve key once; pass it directly so get_annotations_for_item skips the fetch
    if not key:
        key = client.resolve_item_key(path=row.get("path"), title=row.get("title"))
    resolved_key = key or "unmatched"
    anns = client.get_annotations_for_item(item_key=key)
    print(f"### Zotero annotations: {row.get('title') or stem} [{resolved_key}]\n")
    if not anns:
        print("No annotations found in Zotero for this paper.")
        return

    print(f"Found {len(anns)} annotation(s):\n")
    for idx, a in enumerate(anns, 1):
        page_str = f"Page {a['page']}" if a["page"] else "Unknown page"
        type_str = f" ({a['type']})" if a["type"] else ""
        print(f"{idx}. {page_str}{type_str}:")
        if a["text"]:
            print(f'   > "{a["text"]}"')
        if a["comment"]:
            print(f'   *Note: {a["comment"]}*')
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("show", "mark"):
        c = sub.add_parser(cmd)
        c.add_argument("query", nargs="?")
        c.add_argument("--ref")
        if cmd == "show":
            c.add_argument("--chars", type=int, default=1400)
            c.add_argument("--root", type=Path, help="literature root (defaults to $LIT)")
    sub.add_parser("todo")

    rec = sub.add_parser("recommend", help="recommend papers by semantic similarity")
    rec.add_argument("query", help="natural language search query")
    rec.add_argument("--all", action="store_true", help="include already-read papers")
    rec.add_argument("--limit", type=int, default=10, help="max results to show")

    ann = sub.add_parser("annotations", help="show Zotero PDF highlights and notes")
    ann.add_argument("query", nargs="?", help="author or title search query")
    ann.add_argument("--ref", help="bibliography reference number")

    a = ap.parse_args()
    {
        "show": lambda: show(a.query, a.ref, a.chars, corpus_root(a.root)),
        "mark": lambda: mark(a.query, a.ref),
        "todo": todo,
        "recommend": lambda: recommend(a.query, unread_only=not a.all, limit=a.limit),
        "annotations": lambda: annotations(a.query, a.ref),
    }[a.cmd]()


if __name__ == "__main__":
    main()

