"""Zotero local API client for library items and PDF annotations.

Connects to Zotero's local HTTP API (running on port 23119 by default)
without requiring internet access or cloud API keys.

Usage:
    client = ZoteroClient()
    if client.is_available():
        annotations = client.get_annotations_for_item("KEY")
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from related_work.config import clean_alphanumeric


class ZoteroClient:
    """Local Zotero client interfacing with http://127.0.0.1:23119."""

    def __init__(self, base_url: str = "http://127.0.0.1:23119/api/users/0") -> None:
        self.base_url = base_url.rstrip("/")
        self._library_cache: list[dict[str, Any]] | None = None

    def _request(self, endpoint: str, timeout: float = 3.0) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        req = urllib.request.Request(url, headers={"User-Agent": "dqr-literature/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def is_available(self) -> bool:
        """Return True if local Zotero is running and responding."""
        try:
            response = self._request("collections?limit=1", timeout=1.0)
        except (urllib.error.URLError, TimeoutError, OSError):
            return False
        if not isinstance(response, list):
            raise SystemExit("Invalid response from the Zotero local API.")
        return True

    def get_all_library_items(self) -> list[dict[str, Any]]:
        """Fetch the complete local library or fail rather than return a partial snapshot."""
        items: list[dict[str, Any]] = []
        start = 0
        limit = 100
        while True:
            chunk = self._request(f"items?start={start}&limit={limit}")
            if not isinstance(chunk, list) or any(
                not isinstance(item, dict)
                or not isinstance(item.get("key"), str)
                or not isinstance(item.get("data"), dict)
                for item in chunk
            ):
                raise SystemExit(f"Invalid Zotero items response at offset {start}.")
            items.extend(chunk)
            if len(chunk) < limit:
                return items
            start += limit

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
        if items is None:
            if self._library_cache is not None:
                items = self._library_cache
            else:
                items = self.get_all_library_items()
                self._library_cache = items

        if zotero_key:
            if any(item.get("key") == zotero_key for item in items):
                return zotero_key
            raise SystemExit(f"Zotero item {zotero_key} was not found in the library.")

        if path:
            target_name = clean_alphanumeric(Path(path).stem)
            matches = set()
            for item in items:
                d = item.get("data", {})
                if d.get("itemType") == "attachment" and d.get("parentItem"):
                    fn = d.get("filename") or d.get("path", "")
                    if fn and clean_alphanumeric(Path(fn).stem) == target_name:
                        matches.add(d["parentItem"])
            if len(matches) == 1:
                return next(iter(matches))
            if len(matches) > 1:
                raise SystemExit(f"Multiple Zotero items match attachment {path!s}.")

        if title:
            target_title = clean_alphanumeric(title)
            matches = set()
            for item in items:
                d = item.get("data", {})
                if d.get("itemType") not in {"attachment", "note", "annotation"}:
                    t = clean_alphanumeric(d.get("title", ""))
                    if t and (
                        target_title == t
                        or (
                            min(len(target_title), len(t)) > 20
                            and (target_title in t or t in target_title)
                        )
                    ):
                        if item.get("key"):
                            matches.add(item["key"])
            if len(matches) == 1:
                return next(iter(matches))
            if len(matches) > 1:
                raise SystemExit(f"Multiple Zotero items match title {title!r}.")

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
        if items is None:
            if self._library_cache is not None:
                items = self._library_cache
            else:
                items = self.get_all_library_items()
                self._library_cache = items

        if item_key:
            resolved = item_key
        else:
            resolved = self.resolve_item_key(path=path, title=title, items=items)
        if not resolved:
            return []
        all_anns = self.get_annotations_by_top_item(items=items)
        return all_anns.get(resolved, [])
