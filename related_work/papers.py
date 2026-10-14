"""Search the inventory, read paper abstracts, and track reading progress.

Ambiguous matches require an explicit choice; typo suggestions are never guessed.

Usage:
    uv run papers show "metric maze"
    uv run papers show --soa-ref 20
    uv run papers show "metric maze" --chars 500
    uv run papers mark "metric maze"
    uv run papers todo
    uv run papers scaffold "donne and davis"
    uv run papers scaffold --soa-ref 20
"""

import argparse
import csv
import difflib
import os
import re
import subprocess
import sys
import textwrap
import unicodedata
from collections import Counter
from pathlib import Path

import spacy

from related_work.common import get_nlp, load_csv
from related_work.config import (
    INVENTORY,
    NOTES,
    READING_LOG as LOG,
    SOA,
    clean_alphanumeric,
    corpus_root,
    inventory_path,
)

from related_work.zotero import ZoteroClient


def _load(path: Path) -> list[dict[str, str]]:
    return load_csv(path, missing_ok=path == LOG or path == SOA)


def _query_tokens(query: str) -> list[str]:
    return [
        token
        for token in clean_alphanumeric(query).split()
        if token not in {"et", "al", "and"} and not (
            len(token) == 4 and token.isdecimal()
        )
    ]


def _label(row: dict[str, str]) -> str:
    return (
        f"{row.get('author', '')} ({row.get('year') or 'year unknown'}) — "
        f"{row.get('title', '')} [{row.get('path', '')}]"
    )


def _select(candidates: list[dict[str, str]], query: str) -> dict[str, str]:
    print(f"Select a paper matching {query!r}:")
    for number, row in enumerate(candidates, 1):
        print(f"  {number}. {_label(row)}")
    if not sys.stdin.isatty():
        raise SystemExit(
            "Rerun with the exact inventory-relative path or an unambiguous exact title."
        )
    try:
        choice = input("Select a paper number (or press Enter to cancel): ").strip()
    except EOFError as exc:
        raise SystemExit("Paper selection cancelled.") from exc
    if not choice:
        raise SystemExit("Paper selection cancelled.")
    if not choice.isdecimal() or not 1 <= int(choice) <= len(candidates):
        raise SystemExit(f"Invalid selection: {choice!r}")
    return candidates[int(choice) - 1]


def _suggestions(query: str, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    tokens = _query_tokens(query)
    if not tokens:
        return []
    scored = []
    for row in rows:
        row_tokens = set(clean_alphanumeric(f"{row['author']} {row['title']}").split())
        similarities = [
            max(
                (difflib.SequenceMatcher(None, token, candidate).ratio()
                 for candidate in row_tokens),
                default=0,
            )
            for token in tokens
        ]
        if all(score >= 0.85 for score in similarities):
            scored.append((sum(similarities) / len(similarities), row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:5]]


def find(
    query: str | None, soa_ref: str | None
) -> tuple[dict[str, str], str]:
    """Find one inventory paper, prompting only for an explicit terminal choice."""
    if bool(query) == bool(soa_ref):
        raise SystemExit("Provide either a query or --soa-ref.")
    rows = _load(INVENTORY)
    if soa_ref:
        matches = [row for row in _load(SOA) if row["ref"] == soa_ref]
        if not matches:
            raise SystemExit(f"Unknown SoA reference: {soa_ref}")
        if len(matches) > 1:
            raise SystemExit(f"SoA reference {soa_ref} appears more than once.")
        ref = matches[0]
        if ref["local"] != "yes" or not ref.get("local_path"):
            raise SystemExit(f"SoA reference {soa_ref} has no local PDF.")
        path = inventory_path(ref["local_path"])
        row = next((row for row in rows if row.get("path") == path), None)
        if row is None:
            raise SystemExit(
                f"SoA reference {soa_ref} points to a PDF missing from the inventory: {path}"
            )
        return {**row, "citation": ref["citation"], "soa_ref": soa_ref}, "soa"

    if query is None:
        raise SystemExit("Provide either a query or --soa-ref.")
    q_norm = clean_alphanumeric(query)
    q_tokens = set(_query_tokens(query))
    exact_path = [
        row for row in rows if clean_alphanumeric(row["path"]) == q_norm
    ]
    exact_title = [
        row for row in rows if clean_alphanumeric(row["title"]) == q_norm
    ]
    exact = exact_path or exact_title
    if len(exact) == 1:
        return exact[0], "inv"
    if len(exact) > 1:
        return _select(exact, query), "inv"

    # ponytail: the linear scan and token-ratio suggestions fit this corpus;
    # index or rank edit distance only if lookup becomes slow or noisy.
    matches = [
        row
        for row in rows
        if q_tokens
        and q_tokens.issubset(
            set(clean_alphanumeric(f"{row['author']} {row['title']}").split())
        )
    ]
    if len(matches) == 1:
        return matches[0], "inv"
    if len(matches) > 1:
        return _select(matches, query), "inv"

    suggestions = _suggestions(query, rows)
    if suggestions:
        print(f"No exact match for {query!r}; likely matches:")
        return _select(suggestions, query), "inv"
    raise SystemExit(
        f"No inventory match for {query!r}. Use `papers recommend` for a topical search."
    )


def _extract_abstract(sentences: list[str]) -> list[str]:
    """Return the abstract sentences, or [] if none found.

    Finds the sentence containing "abstract" (case-insensitive) near the front
    of the document and collects the following sentences until a section
    heading (an "Introduction"-style line) appears.
    """
    # ponytail: layout heuristics miss unusual PDFs; add rules only for
    # observed extraction failures.
    if not sentences:
        return []
    half = max(1, len(sentences) // 2)
    abstract_idx = None
    for i in range(half):
        if re.search(r"\babstract\b", sentences[i], re.IGNORECASE):
            abstract_idx = i
            break
    if abstract_idx is None:
        return []
    # skip a bare "abstract" heading
    start = abstract_idx + 1 if sentences[abstract_idx].strip().lower() == "abstract" else abstract_idx
    abstract = []
    for sent in sentences[start:]:
        low = sent.strip().lower()
        if re.match(r"^(?:keywords?|index terms?)\b", low):
            break
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


def _extract_paper_body(pdf: Path) -> str:
    """Extract the paper body: labelled abstract, else top-3 extractive summary."""
    if not pdf.is_file():
        raise SystemExit(f"Paper PDF is missing: {pdf}")
    if pdf.stat().st_size == 0:
        raise SystemExit(f"Paper PDF is empty: {pdf}")
    try:
        text = subprocess.run(
            ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True
        ).stdout
    except FileNotFoundError as exc:
        raise SystemExit("pdftotext must be installed and available on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        err = exc.stderr.strip() if exc.stderr else str(exc)
        raise SystemExit(f"pdftotext failed to extract {pdf}: {err}") from exc
    if not text.strip():
        raise SystemExit(f"pdftotext produced no text for {pdf}.")
    doc = get_nlp()(text)
    sentences = [s.text.strip() for s in doc.sents]
    abstract = _extract_abstract(sentences)
    if abstract:
        body = " ".join(abstract)
    else:
        body = " ".join(_extractive_summary(doc, 3))
    if not body.strip():
        raise SystemExit(f"Could not extract an abstract or summary from {pdf}.")
    return body


def _paper_summary(row: dict[str, str]) -> tuple[str, str]:
    if abstract := row.get("abstract", "").strip():
        return abstract, "Abstract"
    pdf = Path(row["path"])
    if not pdf.is_absolute():
        pdf = corpus_root() / pdf
    return _extract_paper_body(pdf), "Extracted summary"


def _slugify(text: str) -> str:
    """Slugify text to ASCII: strip diacritics, lower-case, hyphen-join."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def _strip_subtitle(title: str) -> str:
    """Drop a trailing subtitle: 'Main Title a Subtitle' -> 'Main Title'."""
    low = title.lower()
    for sep in (" a ", " an "):
        idx = low.rfind(sep)
        if idx == -1:
            continue
        # only drop if the tail is short (<=40% of the title), catching
        # 'X a subtitle' but not the middle phrase in a descriptive title
        if idx > len(title) * 0.25 and len(title[idx:]) <= len(title) * 0.4:
            return title[:idx].rstrip()
    return title


def _make_slug(author: str, year: str, title: str, cap: int = 90) -> str:
    """Build a notes/papers/ filename: {author}-{year}-{title}.md.

    Author slug: surnames only, hyphen-joined; more than three authors become
    the first two plus "et al." (matches existing note files).
    Title slug: slugified; a trailing subtitle introduced by " a " / " an "
    is dropped (e.g. "X a comprehensive evaluation" -> "X").
    """
    def _extract_surname(p: str) -> str:
        p = p.strip()
        if "," in p:
            return p.split(",", 1)[0].strip()
        return p.rsplit(None, 1)[-1] if p else "unknown"

    auth = author or ""
    if "&" in auth:
        auth = auth.replace(" & ", " and ")
    if " and " in auth:
        surnames = [_extract_surname(p) for p in auth.split(" and ") if p.strip()]
        if len(surnames) > 3:
            surnames = surnames[:2] + ["et al."]
        author_slug = _slugify(" ".join(surnames))
    elif "," in auth:
        parts = [p.strip() for p in auth.split(",") if p.strip()]
        if any("et al" in p.lower() for p in parts):
            author_slug = _slugify(" ".join(parts))
        elif len(parts) == 2 and len(parts[0].split()) == 1:
            author_slug = _slugify(parts[0])
        else:
            surnames = [_extract_surname(p) for p in parts]
            if len(surnames) > 3:
                surnames = surnames[:2] + ["et al."]
            author_slug = _slugify(" ".join(surnames))
    else:
        author_slug = _slugify(auth.rsplit(None, 1)[-1]) if auth.strip() else "unknown"
    author_slug = author_slug or "unknown"
    title_slug = _slugify(_strip_subtitle(title or "untitled"))
    slug = author_slug
    if year:
        slug += f"-{year}"
    slug += f"-{title_slug}"
    if len(slug) > cap:
        last = slug.rfind("-", 0, cap)
        slug = slug[:last] if last > 0 else slug[:cap]
    return slug


def show(query: str | None, soa_ref: str | None, chars: int) -> None:
    row, source = find(query, soa_ref)
    body, kind = _paper_summary(row)
    body = body[:chars]
    print(
        f"### {row.get('author', '')} ({row.get('year', '')}) — "
        f"{row.get('title', '')}"
    )
    if source == "soa":
        print(f"SoA reference: {soa_ref}")
    print(f"\n{kind}\n")
    print(textwrap.fill(body, 100))


def mark(query: str | None, soa_ref: str | None) -> None:
    row, source = find(query, soa_ref)
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
            "soa_ref": soa_ref or "",
            "citation": row.get("citation", "")[:200],
        }
    )
    tmp = LOG.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["key", "source", "year", "soa_ref", "citation"]
        )
        w.writeheader()
        w.writerows(sorted(entries, key=lambda e: (e["source"], e["key"])))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, LOG)
    print(f"logged: {key}  ({len(entries)} read)")


def todo() -> None:
    entries = _load(LOG)
    read = {e["key"] for e in entries}
    inv = _load(INVENTORY)
    inv_unread = [r for r in inv if Path(r["path"]).stem not in read]
    soa_by_path: dict[str, list[str]] = {}
    for row in _load(SOA):
        if row["local"] == "yes" and row.get("local_path"):
            soa_by_path.setdefault(inventory_path(row["local_path"]), []).append(
                row["ref"]
            )
    print(f"Logged as read: {len(read)} papers")
    print(f"Inventory: {len(inv)} total, {len(inv_unread)} unread")
    print("\nUnread inventory papers:")
    if inv_unread:
        for row in inv_unread:
            refs = soa_by_path.get(row["path"], [])
            legacy = f" [legacy SoA: {', '.join(refs)}]" if refs else ""
            print(
                f"  {row.get('year') or '----'} {row.get('author', '')} — "
                f"{row.get('title', '')} [{row['path']}]{legacy}"
            )
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


def annotations(query: str | None, soa_ref: str | None) -> None:
    row, _ = find(query, soa_ref)
    key = row.get("zotero_key")
    stem = Path(row["path"]).stem

    client = ZoteroClient()
    if not client.is_available():
        raise SystemExit("Zotero local API is not running. Start Zotero to fetch annotations.")

    items = client.get_all_library_items()
    key = client.resolve_item_key(
        zotero_key=key, path=row.get("path"), title=row.get("title"), items=items
    )
    if not key:
        raise SystemExit(f"Could not match {row.get('title') or stem!r} in Zotero.")
    anns = client.get_annotations_for_item(item_key=key, items=items)
    print(f"### Zotero annotations: {row.get('title') or stem} [{key}]\n")
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


def scaffold(query: str | None, soa_ref: str | None, force: bool = False) -> None:
    """Generate a starter note from Zotero highlights + a PDF summary.

    Looks up the paper, extracts a summary from its PDF, and writes
    notes/papers/<slug>.md with the title, summary, and Zotero highlights
    if the library is running. Skips existing notes unless --force is given.
    """
    row, _ = find(query, soa_ref)
    slug = _make_slug(
        row.get("author") or "",
        row.get("year") or "",
        row.get("title") or "",
    )
    out = NOTES / f"{slug}.md"
    if out.exists() and not force:
        print(f"already exists: {out}\n(use --force to overwrite)")
        return

    body, kind = _paper_summary(row)
    body = body.replace("\n", " ")[:5000]

    client = ZoteroClient()
    if client.is_available():
        items = client.get_all_library_items()
        key = client.resolve_item_key(
            zotero_key=row.get("zotero_key"),
            path=row.get("path"),
            title=row.get("title"),
            items=items,
        )
        if not key:
            raise SystemExit(
                f"Could not match {row.get('title') or row['path']!r} in Zotero."
            )
        anns = client.get_annotations_for_item(item_key=key, items=items)
    else:
        anns = None

    lines = [
        f"# {row.get('author') or ''} ({row.get('year') or ''}) — {row.get('title') or ''}",
        "",
        f"> **{kind}**",
        f"> {body}",
        "",
        "## Zotero highlights",
        "",
    ]
    if anns is None:
        lines.append("<!-- Zotero unavailable — add highlights manually -->")
    else:
        for i, a in enumerate(anns, 1):
            page = f"Page {a['page']}" if a["page"] else "Page unknown"
            type_ = f" ({a['type']})" if a["type"] else ""
            lines.append(f"{i}. {page}{type_}:")
            if a["text"]:
                lines.append(f'   > "{a["text"]}"')
            if a["comment"]:
                lines.append(f'   *Note: {a["comment"]}*')
            lines.append("")
    lines.extend(["## Notes", "", "<!-- your notes here -->"])

    NOTES.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote: {out}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("show", "mark"):
        c = sub.add_parser(cmd)
        selector = c.add_mutually_exclusive_group()
        selector.add_argument(
            "query",
            nargs="?",
            help="author/title search or exact inventory-relative PDF path",
        )
        selector.add_argument(
            "--soa-ref", help="legacy reference number in data/soa_citations.csv"
        )
        if cmd == "show":
            c.add_argument(
                "--chars", type=int, default=1400, help="maximum abstract text to print"
            )
    sub.add_parser("todo")

    rec = sub.add_parser("recommend", help="recommend papers by semantic similarity")
    rec.add_argument("query", help="natural language search query")
    rec.add_argument("--all", action="store_true", help="include already-read papers")
    rec.add_argument("--limit", type=int, default=10, help="max results to show")

    ann = sub.add_parser("annotations", help="show Zotero PDF highlights and notes")
    selector = ann.add_mutually_exclusive_group()
    selector.add_argument("query", nargs="?", help="author or title search query")
    selector.add_argument(
        "--soa-ref", help="legacy reference number in data/soa_citations.csv"
    )

    sca = sub.add_parser("scaffold", help="generate a starter note from highlights + PDF summary")
    selector = sca.add_mutually_exclusive_group()
    selector.add_argument("query", nargs="?", help="author or title search query")
    selector.add_argument(
        "--soa-ref", help="legacy reference number in data/soa_citations.csv"
    )
    sca.add_argument("--force", action="store_true", help="overwrite existing note")

    a = ap.parse_args()
    {
        "show": lambda: show(a.query, a.soa_ref, a.chars),
        "mark": lambda: mark(a.query, a.soa_ref),
        "todo": todo,
        "recommend": lambda: recommend(a.query, unread_only=not a.all, limit=a.limit),
        "annotations": lambda: annotations(a.query, a.soa_ref),
        "scaffold": lambda: scaffold(a.query, a.soa_ref, a.force),
    }[a.cmd]()


if __name__ == "__main__":
    main()
