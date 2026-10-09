import contextlib
import csv
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from related_work.inventory import _zotero_items, enrich, main
from related_work.config import corpus_root


class TestZoteroInventory(unittest.TestCase):
    def test_cli_defaults_to_lit_and_repository_inventory_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Literature"
            root.mkdir()
            (root / "2020 Local Title.pdf").touch()
            output = Path(temp) / "inventory.csv"
            with (
                patch("related_work.inventory.corpus_root", return_value=root),
                patch("related_work.inventory.INVENTORY", output),
                patch("sys.argv", ["inventory"]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                main()

            with output.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                row = next(reader)
            self.assertEqual(
                reader.fieldnames,
                ["year", "author", "title", "path", "zotero_key", "abstract"],
            )
            self.assertEqual(row["path"], "2020 Local Title.pdf")
            self.assertEqual(row["zotero_key"], "")

    def test_filesystem_refresh_keeps_existing_zotero_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Literature"
            root.mkdir()
            (root / "2020 Local Title.pdf").touch()
            output = Path(temp) / "inventory.csv"
            with output.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=[
                        "year",
                        "author",
                        "title",
                        "path",
                        "zotero_key",
                        "abstract",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "year": "2020",
                        "author": "Zotero Author",
                        "title": "Published Title",
                        "path": "2020 Local Title.pdf",
                        "zotero_key": "ITEM0001",
                        "abstract": "Abstract text.",
                    }
                )
            with (
                patch("related_work.inventory.corpus_root", return_value=root),
                patch("related_work.inventory.INVENTORY", output),
                patch("sys.argv", ["inventory"]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                main()

            with output.open(encoding="utf-8", newline="") as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row["author"], "Zotero Author")
            self.assertEqual(row["title"], "Published Title")
            self.assertEqual(row["zotero_key"], "ITEM0001")
            self.assertEqual(row["abstract"], "Abstract text.")

    def test_zotero_cli_enriches_canonical_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Literature"
            root.mkdir()
            (root / "2020 Local Title.pdf").touch()
            output = Path(temp) / "inventory.csv"
            items = [
                {
                    "data": {
                        "key": "ITEM0001",
                        "itemType": "journalArticle",
                        "title": "Published Title",
                        "date": "2020",
                        "abstractNote": "Abstract text.",
                    }
                },
                {
                    "data": {
                        "key": "CHILD001",
                        "parentItem": "ITEM0001",
                        "itemType": "attachment",
                        "filename": "2020 Local Title.pdf",
                        "contentType": "application/pdf",
                    }
                },
            ]
            with (
                patch("related_work.inventory.corpus_root", return_value=root),
                patch("related_work.inventory.INVENTORY", output),
                patch("related_work.inventory._zotero_items", return_value=items),
                patch("sys.argv", ["inventory", "--zotero-local"]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                main()

            with output.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(
                    reader.fieldnames,
                    ["year", "author", "title", "path", "zotero_key", "abstract"],
                )
                row = next(reader)
            self.assertEqual(row["path"], "2020 Local Title.pdf")
            self.assertEqual(row["title"], "Published Title")
            self.assertEqual(row["zotero_key"], "ITEM0001")
            self.assertEqual(row["abstract"], "Abstract text.")

    def test_attachment_match_adds_metadata_and_keeps_pdf_path(self):
        rows = [
            {
                "year": "2021",
                "author": "Filename Author",
                "title": "Filename Title",
                "path": "papers/local.pdf",
            }
        ]
        items = [
            {
                "data": {
                    "key": "PARENT01",
                    "itemType": "journalArticle",
                    "title": "Published Title",
                    "date": "2021-05",
                    "creators": [
                        {
                            "creatorType": "author",
                            "firstName": "Ada",
                            "lastName": "Lovelace",
                        }
                    ],
                    "abstractNote": "An abstract.",
                }
            },
            {
                "data": {
                    "key": "CHILD001",
                    "parentItem": "PARENT01",
                    "itemType": "attachment",
                    "path": "attachments:storage/local.pdf",
                    "contentType": "application/pdf",
                }
            },
        ]

        enriched, matched, ambiguous = enrich(rows, items)

        self.assertEqual(matched, 1)
        self.assertEqual(ambiguous, 0)
        self.assertEqual(enriched[0]["path"], "papers/local.pdf")
        self.assertEqual(enriched[0]["title"], "Published Title")
        self.assertEqual(enriched[0]["author"], "Ada Lovelace")
        self.assertEqual(enriched[0]["zotero_key"], "PARENT01")
        self.assertEqual(enriched[0]["abstract"], "An abstract.")

    def test_exact_normalized_title_and_year_match(self):
        rows = [
            {"year": "2020", "author": "", "title": "A Clean-Title!", "path": "a.pdf"}
        ]
        items = [
            {
                "data": {
                    "key": "ITEM0001",
                    "itemType": "journalArticle",
                    "title": "A clean title",
                    "date": "2020",
                }
            }
        ]

        enriched, matched, ambiguous = enrich(rows, items)

        self.assertEqual(matched, 1)
        self.assertEqual(ambiguous, 0)
        self.assertEqual(enriched[0]["zotero_key"], "ITEM0001")

    def test_ambiguous_duplicate_titles_are_not_enriched(self):
        rows = [
            {"year": "2020", "author": "Local", "title": "Same Paper", "path": "a.pdf"}
        ]
        items = [
            {
                "data": {
                    "key": key,
                    "itemType": "journalArticle",
                    "title": "Same Paper",
                    "date": "2020",
                }
            }
            for key in ("ITEM0001", "ITEM0002")
        ]

        enriched, matched, ambiguous = enrich(rows, items)

        self.assertEqual(matched, 0)
        self.assertEqual(ambiguous, 1)
        self.assertEqual(enriched[0]["zotero_key"], "")
        self.assertEqual(enriched[0]["author"], "Local")

    def test_attachment_with_conflicting_year_is_not_matched(self):
        rows = [
            {"year": "2021", "author": "", "title": "", "path": "paper.pdf"}
        ]
        items = [
            {
                "data": {
                    "key": "ITEM0001",
                    "itemType": "journalArticle",
                    "title": "Paper",
                    "date": "2020",
                }
            },
            {
                "data": {
                    "key": "CHILD001",
                    "parentItem": "ITEM0001",
                    "itemType": "attachment",
                    "filename": "paper.pdf",
                    "contentType": "application/pdf",
                }
            },
        ]

        enriched, matched, ambiguous = enrich(rows, items)

        self.assertEqual((matched, ambiguous), (0, 0))
        self.assertEqual(enriched[0]["zotero_key"], "")

    def test_local_client_is_read_only_and_uses_all_items(self):
        calls = []

        class FakeZotero:
            def __init__(self, *args, **kwargs):
                calls.append((args, kwargs))

            def items(self):
                calls.append("items")
                return ["first-page"]

            def everything(self, items):
                calls.append(("everything", items))
                return ["all-items"]

        module = types.ModuleType("pyzotero")
        module.Zotero = FakeZotero
        with patch.dict(sys.modules, {"pyzotero": module}):
            items = _zotero_items()

        self.assertEqual(items, ["all-items"])
        self.assertEqual(calls[0], (("0", "user"), {"local": True}))
        self.assertEqual(calls[1:], ["items", ("everything", ["first-page"])])


if __name__ == "__main__":
    unittest.main()
