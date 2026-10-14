"""Semantic document vector search and ranking across the paper inventory.

Uses spaCy's en_core_web_md embeddings to match natural language queries
against paper titles and abstracts. Vector representations are cached
to disk and automatically refreshed when data/inventory.csv changes.

Usage:
    from related_work.semantic import rank_inventory
    results = rank_inventory(
        "overhead crane sensor fault detection", unread_only=True
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import warnings
import zipfile

import numpy as np

from related_work.common import get_nlp, load_csv
from related_work.config import DATA, INVENTORY, READING_LOG, clean_alphanumeric

CACHE_FILE = DATA / ".vector_cache.npz"


def _load_read_keys(log_path: Path) -> set[str]:
    return {
        row["key"]
        for row in load_csv(log_path, missing_ok=True)
        if row.get("key")
    }


def get_inventory_vectors(
    inventory_path: Path = INVENTORY, cache_path: Path | None = None
) -> tuple[list[dict[str, str]], np.ndarray]:
    """Return (rows, normalized_vector_matrix) with mtime-aware disk caching."""
    rows = load_csv(inventory_path)
    if not rows:
        return [], np.zeros((0, 300), dtype=np.float32)

    if cache_path is None and inventory_path.resolve() == INVENTORY.resolve():
        cache_path = CACHE_FILE

    current_mtime = inventory_path.stat().st_mtime if inventory_path.exists() else 0.0

    if cache_path is not None and cache_path.exists():
        try:
            with np.load(cache_path) as cached:
                if cached["mtime"] == current_mtime and len(cached["vecs"]) == len(rows):
                    return rows, cached["vecs"]
        except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile) as exc:
            warnings.warn(f"Recomputing invalid vector cache {cache_path}: {exc}")

    nlp = get_nlp()
    texts = [f"{r.get('title', '')}. {r.get('abstract', '')}" for r in rows]
    docs = list(nlp.pipe(texts, batch_size=64, disable=["parser", "ner"]))

    raw_vecs = np.array([doc.vector for doc in docs], dtype=np.float32)
    norms = np.linalg.norm(raw_vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normed_vecs = raw_vecs / norms

    if cache_path is not None:
        try:
            np.savez(cache_path, vecs=normed_vecs, mtime=current_mtime)
        except OSError as exc:
            warnings.warn(f"Could not write vector cache {cache_path}: {exc}")

    return rows, normed_vecs


def rank_inventory(
    query: str,
    *,
    unread_only: bool = True,
    top_k: int = 10,
    inventory_path: Path = INVENTORY,
    reading_log_path: Path = READING_LOG,
    cache_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Rank by semantic similarity, boosted by exact title and abstract terms."""
    rows, matrix = get_inventory_vectors(inventory_path, cache_path=cache_path)
    if len(rows) == 0:
        return []

    read_keys = _load_read_keys(reading_log_path)
    nlp = get_nlp()
    q_doc = nlp(query, disable=["parser", "ner"])
    q_vec = q_doc.vector.astype(np.float32)
    q_norm = np.linalg.norm(q_vec)
    if q_norm == 0:
        return []
    q_normed = q_vec / q_norm
    query_terms = {
        term
        for token in q_doc
        if token.is_alpha and not token.is_stop
        for term in clean_alphanumeric(token.text).split()
    }

    semantic_scores = matrix @ q_normed

    ranked: list[dict[str, Any]] = []
    for semantic_score, row in zip(semantic_scores, rows):
        stem = Path(row["path"]).stem
        is_read = stem in read_keys
        if unread_only and is_read:
            continue
        if query_terms:
            title_terms = set(clean_alphanumeric(row.get("title", "")).split())
            paper_terms = set(
                clean_alphanumeric(
                    f"{row.get('title', '')} {row.get('abstract', '')}"
                ).split()
            )
            title_coverage = len(query_terms & title_terms) / len(query_terms)
            paper_coverage = len(query_terms & paper_terms) / len(query_terms)
            keyword_score = 0.75 * title_coverage + 0.25 * paper_coverage
            # ponytail: fixed 75/25 blend; tune only against a judged query set.
            score = 0.75 * max(float(semantic_score), 0.0) + 0.25 * keyword_score
        else:
            score = float(semantic_score)
        ranked.append(
            {
                "score": float(score),
                "is_read": is_read,
                "key": stem,
                "year": row.get("year", ""),
                "author": row.get("author", ""),
                "title": row.get("title", ""),
                "path": row.get("path", ""),
                "zotero_key": row.get("zotero_key", ""),
                "abstract": row.get("abstract", ""),
            }
        )

    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:top_k]
