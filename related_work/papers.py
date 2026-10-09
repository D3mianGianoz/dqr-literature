"""Read and track papers in the local collection.

Compact abstract extraction, plus a machine-checkable reading log so read/unread
counts stop being tracked in prose (they have been wrong twice).

Usage:
    uv run python -m related_work.papers show "metric maze"
    uv run python -m related_work.papers show --ref 20
    uv run python -m related_work.papers mark "metric maze"
    uv run python -m related_work.papers todo
    uv run python -m related_work.papers scaffold "donne and davis"
    uv run python -m related_work.papers scaffold --ref 20
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
    NOTES,
    READING_LOG as LOG,
    SOA,
    corpus_root,
    inventory_path,
)

from related_work.zotero import ZoteroClient

import unicodedata

nlp = spacy.load("en_core_web_md")


def _load(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8"))) if path.exists() else []


def _norm_text(s: str) -> str:
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


def _extract_paper_body(pdf: Path) -> str:
    """Extract the paper body: labelled abstract, else top-3 extractive summary."""
    try:
        text = subprocess.run(
            ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit("pdftotext must be installed and available on PATH.") from exc
    flat = re.sub(r"\s+", " ", text)
    doc = nlp(flat)
    sentences = [s.text.strip() for s in doc.sents]
    abstract = _extract_abstract(sentences)
    if abstract:
        body = " ".join(abstract)
    else:
        body = " ".join(_extractive_summary(doc, 3))
    return body


def _slugify(text: str) -> str:
    """Slugify text to ASCII: strip diacritics, lower-case, hyphen-join."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return re.sub(r"-+", "-", text)


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
    auth = author or ""
    if "&" in auth:
        auth = auth.replace(" & ", " and ")
    if " and " in auth:
        surnames = [p.strip().rsplit(None, 1)[-1] for p in auth.split(" and ") if p.strip()]
        if len(surnames) > 3:
            surnames = surnames[:2] + ["et al."]
        author_slug = _slugify(" ".join(surnames))
    elif "," in auth:
        author_slug = _slugify(" ".join(p.strip() for p in auth.split(",")))
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


def show(
    query: str | None, ref: str | None, chars: int, root: Path = Path(".")
) -> None:
    row, source = find(query, ref)
    pdf = Path(row["path"])
    if not pdf.is_absolute():
        pdf = root / pdf
    body = _extract_paper_body(pdf)
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


def scaffold(query: str | None, ref: str | None, force: bool = False, root: Path | None = None) -> None:
    """Generate a starter note from Zotero highlights + a PDF summary.

    Looks up the paper, extracts a summary from its PDF, and writes
    notes/papers/<slug>.md with the title, summary, and Zotero highlights
    if the library is running. Skips existing notes unless --force is given.
    """
    row, source = find(query, ref)
    pdf = Path(row["path"])
    if not pdf.is_absolute():
        pdf = corpus_root(root) / pdf
    body = _extract_paper_body(pdf)
    body = body.replace("\n", " ")[:5000]

    slug = _make_slug(
        row.get("author") or "",
        row.get("year") or "",
        row.get("title") or "",
    )
    out = NOTES / f"{slug}.md"
    if out.exists() and not force:
        print(f"already exists: {out}\n(use --force to overwrite)")
        return

    client = ZoteroClient()
    if client.is_available():
        key = row.get("zotero_key")
        if not key:
            key = client.resolve_item_key(path=row.get("path"), title=row.get("title"))
        anns = client.get_annotations_for_item(item_key=key)
    else:
        anns = None

    lines = [
        f"# {row.get('author') or ''} ({row.get('year') or ''}) — {row.get('title') or ''}",
        "",
        "> **Abstract / Summary**",
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
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for cmd in ("show", "mark"):
        c = sub.add_parser(cmd)
        c.add_argument("query", nargs="?")
        c.add_argument("--ref")
        if cmd == "show":
            c.add_argument("--chars", type=int, default=1400)
            c.add_argument("--root", type=Path, help="literature root (defaults to [tool.dqr-literature].lit_root in pyproject.toml)")
    sub.add_parser("todo")

    rec = sub.add_parser("recommend", help="recommend papers by semantic similarity")
    rec.add_argument("query", help="natural language search query")
    rec.add_argument("--all", action="store_true", help="include already-read papers")
    rec.add_argument("--limit", type=int, default=10, help="max results to show")

    ann = sub.add_parser("annotations", help="show Zotero PDF highlights and notes")
    ann.add_argument("query", nargs="?", help="author or title search query")
    ann.add_argument("--ref", help="bibliography reference number")

    sca = sub.add_parser("scaffold", help="generate a starter note from highlights + PDF summary")
    sca.add_argument("query", nargs="?", help="author or title search query")
    sca.add_argument("--ref", help="bibliography reference number")
    sca.add_argument("--root", type=Path, help="literature root (defaults to [tool.dqr-literature].lit_root in pyproject.toml)")
    sca.add_argument("--force", action="store_true", help="overwrite existing note")

    a = ap.parse_args()
    {
        "show": lambda: show(a.query, a.ref, a.chars, corpus_root(a.root)),
        "mark": lambda: mark(a.query, a.ref),
        "todo": todo,
        "recommend": lambda: recommend(a.query, unread_only=not a.all, limit=a.limit),
        "annotations": lambda: annotations(a.query, a.ref),
        "scaffold": lambda: scaffold(a.query, a.ref, a.force, a.root),
    }[a.cmd]()


if __name__ == "__main__":
    main()

