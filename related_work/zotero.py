"""Zotero local API client for collections and PDF annotations.

Connects to Zotero's local HTTP API (running on port 23119 by default)
without requiring internet access or cloud API keys.

Usage:
    client = ZoteroClient()
    if client.is_available():
        collections = client.get_collections()
        annotations = client.get_annotations_for_item("KEY")
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class ZoteroClient:
    """Local Zotero client interfacing with http://127.0.0.1:23119."""

    def __init__(self, base_url: str = "http://127.0.0.1:23119/api/users/0") -> None:
        self.base_url = base_url.rstrip("/")

    def _request(self, endpoint: str, timeout: float = 3.0) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        req = urllib.request.Request(url, headers={"User-Agent": "dqr-literature/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def is_available(self) -> bool:
        """Return True if local Zotero is running and responding."""
        try:
            self._request("collections?limit=1", timeout=1.0)
            return True
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def get_collections(self) -> dict[str, dict[str, str]]:
        """Return collection_key -> {'name': name, 'path': 'parent/name'}."""
        try:
            raw = self._request("collections")
        except Exception:
            return {}

        by_key = {c["key"]: c.get("data", {}) for c in raw if "key" in c}

        def _resolve_path(k: str, visited: set[str] | None = None) -> str:
            visited = visited or set()
            if k in visited or k not in by_key:
                return by_key.get(k, {}).get("name", k)
            visited.add(k)
            data = by_key[k]
            parent = data.get("parentCollection")
            name = data.get("name", "")
            if parent and parent in by_key:
                return f"{_resolve_path(parent, visited)}/{name}"
            return name

        result = {}
        for key, data in by_key.items():
            result[key] = {
                "name": data.get("name", ""),
                "parent": data.get("parentCollection") or "",
                "path": _resolve_path(key),
            }
        return result

    def get_all_library_items(self) -> list[dict[str, Any]]:
        """Retrieve all items using pyzotero if available, or paged urllib."""
        try:
            from pyzotero import Zotero  # type: ignore

            z = Zotero("0", "user", local=True)
            return z.everything(z.items())
        except Exception:
            # Paged fallback via urllib
            items: list[dict[str, Any]] = []
            start = 0
            limit = 100
            while True:
                try:
                    chunk = self._request(f"items?start={start}&limit={limit}")
                except Exception:
                    break
                if not chunk:
                    break
                items.extend(chunk)
                if len(chunk) < limit:
                    break
                start += limit
            return items

    def get_annotations_by_top_item(
        self, items: list[dict[str, Any]] | None = None
    ) -> dict[str, list[dict[str, str]]]:
        """Map top_item_key -> list of annotation dicts.

        Pass *items* to reuse an already-fetched library snapshot and avoid a
        redundant round-trip to Zotero.
        """
        if items is None:
            items = self.get_all_library_items()
        attachments: dict[str, str] = {}
        for item in items:
            data = item.get("data", {})
            if data.get("itemType") == "attachment" and data.get("parentItem"):
                attachments[item["key"]] = data["parentItem"]

        grouped: dict[str, list[dict[str, str]]] = {}
        for item in items:
            data = item.get("data", {})
            if data.get("itemType") == "annotation":
                parent_att = data.get("parentItem")
                top_key = attachments.get(parent_att)
                if top_key:
                    grouped.setdefault(top_key, []).append(
                        {
                            "text": data.get("annotationText", "").strip(),
                            "comment": data.get("annotationComment", "").strip(),
                            "page": str(data.get("annotationPageLabel", "")).strip(),
                            "type": data.get("annotationType", ""),
                            "color": data.get("annotationColor", ""),
                            "date": data.get("dateModified", ""),
                        }
                    )

        # Sort annotations by page if integer-convertible
        for key, ann_list in grouped.items():
            ann_list.sort(key=lambda a: int(a["page"]) if a["page"].isdigit() else 999999)

        return grouped

    def resolve_item_key(
        self,
        zotero_key: str | None = None,
        path: str | Path | None = None,
        title: str | None = None,
        items: list[dict[str, Any]] | None = None,
    ) -> str | None:
        """Resolve a top-level Zotero item key via key, attachment filename, or title.

        Pass *items* to reuse an already-fetched library snapshot and avoid a
        redundant round-trip to Zotero.
        """
        if zotero_key:
            return zotero_key

        import unicodedata

        def _norm(s: str) -> str:
            return "".join(
                c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
            ).casefold().strip()

        def _clean_alphanumeric(s: str) -> str:
            normed = _norm(s)
            return " ".join("".join(c if c.isalnum() else " " for c in normed).split())

        if items is None:
            items = self.get_all_library_items()

        if path:
            target_name = _clean_alphanumeric(Path(path).stem)
            for item in items:
                d = item.get("data", {})
                if d.get("itemType") == "attachment" and d.get("parentItem"):
                    fn = d.get("filename") or d.get("path", "")
                    if fn and _clean_alphanumeric(Path(fn).stem) == target_name:
                        return d["parentItem"]

        if title:
            target_title = _clean_alphanumeric(title)
            for item in items:
                d = item.get("data", {})
                if d.get("itemType") not in {"attachment", "note", "annotation"}:
                    t = _clean_alphanumeric(d.get("title", ""))
                    if t and (target_title == t or (len(target_title) > 20 and (target_title in t or t in target_title))):
                        return item.get("key")

        return None

    def get_annotations_for_item(
        self,
        item_key: str | None = None,
        path: str | Path | None = None,
        title: str | None = None,
        items: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, str]]:
        """Return annotations for an item, resolving key if needed.

        Fetches the full library only once and shares the snapshot between key
        resolution and annotation grouping.
        """
        if item_key:
            resolved = item_key
        else:
            if items is None:
                items = self.get_all_library_items()
            resolved = self.resolve_item_key(path=path, title=title, items=items)
        if not resolved:
            return []
        all_anns = self.get_annotations_by_top_item(items=items)
        return all_anns.get(resolved, [])
