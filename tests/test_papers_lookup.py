import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from related_work import papers


class TestPaperLookup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.inventory = root / "inventory.csv"
        self.soa = root / "soa.csv"
        self.inventory.write_text(
            "year,author,title,path,zotero_key,abstract\n"
            "2026,Damiano Gianotti and Ada Smith,Assessing Reliability of Sensor Data,2026/paper.pdf,K1,An abstract.\n"
            "2024,Alice Jones,Data Quality in Industrial Systems,books/quality.pdf,K2,\n"
            "2023,Bob Lee,Data Quality for Sensor Networks,archive/sensors.pdf,K3,\n",
            encoding="utf-8",
        )
        self.soa.write_text(
            "ref,year,surnames,local,method,local_path,citation\n"
            "20,2026,gianotti|smith,yes,exact,Literature/2026/paper.pdf,Old citation\n",
            encoding="utf-8",
        )
        self.patches = (
            patch.object(papers, "INVENTORY", self.inventory),
            patch.object(papers, "SOA", self.soa),
        )
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp.cleanup()

    def test_normalizes_case_accents_punctuation_and_et_al(self):
        row, source = papers.find("Gianotti et al.", None)
        self.assertEqual(source, "inv")
        self.assertEqual(row["path"], "2026/paper.pdf")
        row, _ = papers.find("reliability assessing", None)
        self.assertEqual(row["path"], "2026/paper.pdf")

    def test_exact_relative_path_and_title_select_directly(self):
        self.assertEqual(papers.find("archive/sensors.pdf", None)[0]["author"], "Bob Lee")
        self.assertEqual(
            papers.find("data quality for sensor networks", None)[0]["path"],
            "archive/sensors.pdf",
        )

    def test_typo_only_suggests_and_never_guesses_non_interactively(self):
        output = io.StringIO()
        with (
            patch("related_work.papers.sys.stdin.isatty", return_value=False),
            contextlib.redirect_stdout(output),
            self.assertRaisesRegex(SystemExit, "exact inventory-relative path"),
        ):
            papers.find("Assesing reliability", None)
        self.assertIn("likely matches", output.getvalue())
        self.assertIn("2026/paper.pdf", output.getvalue())

    def test_ambiguous_query_fails_non_interactively(self):
        output = io.StringIO()
        with (
            patch("related_work.papers.sys.stdin.isatty", return_value=False),
            contextlib.redirect_stdout(output),
            self.assertRaisesRegex(SystemExit, "exact inventory-relative path"),
        ):
            papers.find("data quality", None)
        self.assertIn("books/quality.pdf", output.getvalue())
        self.assertIn("archive/sensors.pdf", output.getvalue())

    def test_interactive_selection_uses_numbered_candidate(self):
        with (
            patch("related_work.papers.sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value="2"),
        ):
            row, _ = papers.find("data quality", None)
        self.assertEqual(row["path"], "archive/sensors.pdf")

    def test_cancelled_selection_does_not_write_reading_log(self):
        log = Path(self.temp.name) / "reading_log.csv"
        with (
            patch.object(papers, "LOG", log),
            patch("related_work.papers.sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value=""),
            self.assertRaisesRegex(SystemExit, "cancelled"),
        ):
            papers.mark("data quality", None)
        self.assertFalse(log.exists())

    def test_typo_suggestion_requires_explicit_terminal_choice(self):
        with (
            patch("related_work.papers.sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value="1"),
        ):
            row, _ = papers.find("Assesing reliability", None)
        self.assertEqual(row["path"], "2026/paper.pdf")

    def test_soa_reference_returns_current_inventory_metadata(self):
        row, source = papers.find(None, "20")
        self.assertEqual(source, "soa")
        self.assertEqual(row["abstract"], "An abstract.")
        self.assertEqual(row["zotero_key"], "K1")
        self.assertEqual(row["soa_ref"], "20")
        self.assertEqual(row["citation"], "Old citation")

    def test_mark_preserves_legacy_reference_and_is_idempotent(self):
        log = Path(self.temp.name) / "reading_log.csv"
        log.write_text("key,source,year,soa_ref,citation\n", encoding="utf-8")
        with patch.object(papers, "LOG", log), contextlib.redirect_stdout(io.StringIO()):
            papers.mark(None, "20")
            papers.mark(None, "20")
        rows = papers._load(log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "soa")
        self.assertEqual(rows[0]["soa_ref"], "20")

    def test_todo_lists_inventory_and_labels_legacy_reference(self):
        log = Path(self.temp.name) / "reading_log.csv"
        log.write_text("key,source,year,soa_ref,citation\n", encoding="utf-8")
        output = io.StringIO()
        with (
            patch.object(papers, "LOG", log),
            contextlib.redirect_stdout(output),
        ):
            papers.todo()
        text = output.getvalue()
        self.assertIn("Inventory: 3 total, 3 unread", text)
        self.assertIn("[legacy SoA: 20]", text)
        self.assertIn("archive/sensors.pdf", text)

    def test_show_uses_inventory_abstract_without_resolving_pdf_root(self):
        output = io.StringIO()
        with (
            patch.object(
                papers,
                "find",
                return_value=(
                    {
                        "author": "Ada Lovelace",
                        "year": "2020",
                        "title": "A Paper",
                        "path": "missing.pdf",
                        "abstract": "Inventory abstract.",
                    },
                    "inv",
                ),
            ),
            patch.object(papers, "corpus_root", side_effect=AssertionError),
            patch.object(papers, "_extract_paper_body", side_effect=AssertionError),
            contextlib.redirect_stdout(output),
        ):
            papers.show("paper", None, 1000)
        self.assertIn("Abstract", output.getvalue())
        self.assertIn("Inventory abstract.", output.getvalue())

    def test_empty_pdf_extraction_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp:
            pdf = Path(temp) / "paper.pdf"
            pdf.write_bytes(b"not empty")
            with patch.object(
                papers, "subprocess"
            ) as process:
                process.run.return_value = SimpleNamespace(stdout=" \n ")
                with self.assertRaisesRegex(SystemExit, "produced no text"):
                    papers._extract_paper_body(pdf)

    def test_invalid_selectors_and_stale_reference_fail(self):
        with self.assertRaisesRegex(SystemExit, "--soa-ref"):
            papers.find(None, None)
        with self.assertRaisesRegex(SystemExit, "either a query"):
            papers.find("query", "20")
        self.soa.write_text(
            self.soa.read_text(encoding="utf-8").replace(
                "2026/paper.pdf", "Literature/missing.pdf"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SystemExit, "missing from the inventory"):
            papers.find(None, "20")


if __name__ == "__main__":
    unittest.main()
