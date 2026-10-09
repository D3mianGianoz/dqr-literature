import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from related_work import semantic
from related_work.papers import _make_slug


class TestScaffold(unittest.TestCase):
    def test_scaffold_subcommand_registered(self):
        """The scaffold subcommand is registered and accepts --force / --ref."""
        r = subprocess.run(
            [sys.executable, "-m", "related_work.papers", "scaffold", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("scaffold", r.stdout)
        self.assertIn("--force", r.stdout)
        self.assertIn("--root", r.stdout)

    def test_scaffold_cli_skips_existing_note(self):
        """Existing note files are not overwritten without --force."""
        r = subprocess.run(
            [sys.executable, "-m", "related_work.papers", "scaffold", "donne and davis"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("already exists", r.stdout)
        self.assertNotIn("wrote:", r.stdout)

    def test_scaffold_offline_graceful(self):
        """With Zotero down, scaffold still writes a note with a stub comment."""
        from unittest.mock import patch
        from related_work import papers as p

        notes = Path(tempfile.mkdtemp()) / "notes" / "papers"
        row = {
            "path": "Zpapers/2023/crane.pdf",
            "year": "2023",
            "author": "Alice Smith",
            "title": "Overhead Crane Fault Detection",
            "zotero_key": "K1",
        }
        with patch.object(p, "NOTES", notes), \
             patch.object(p, "find", return_value=(row, "inv")), \
             patch.object(p, "_extract_paper_body", return_value="A summary of the paper."), \
             patch.object(p, "ZoteroClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.is_available.return_value = False
            p.scaffold(query="crane", ref=None, force=True, root=Path("."))
        out = notes / "smith-2023-overhead-crane-fault-detection.md"
        self.assertTrue(out.exists())
        content = out.read_text()
        self.assertIn("# Alice Smith (2023) \u2014 Overhead Crane Fault Detection", content)
        self.assertIn("> A summary of the paper.", content)
        self.assertIn("## Zotero highlights", content)
        self.assertIn("<!-- Zotero unavailable \u2014 add highlights manually -->", content)
        self.assertIn("<!-- your notes here -->", content)

    def test_scaffold_writes_highlights(self):
        """With Zotero available, highlights and comments are included."""
        from unittest.mock import patch
        from related_work import papers as p

        notes = Path(tempfile.mkdtemp()) / "notes" / "papers"
        row = {
            "path": "Zpapers/2023/crane.pdf",
            "year": "2023",
            "author": "Alice Smith",
            "title": "Overhead Crane Fault Detection",
            "zotero_key": "K1",
        }
        annotations = [
            {
                "text": "important finding",
                "comment": "my note",
                "page": "5",
                "type": "highlight",
                "color": "yellow",
                "date": "",
            },
            {
                "text": "another point",
                "comment": "",
                "page": "12",
                "type": "underline",
                "color": "green",
                "date": "",
            },
        ]
        with patch.object(p, "NOTES", notes), \
             patch.object(p, "find", return_value=(row, "inv")), \
             patch.object(p, "_extract_paper_body", return_value="A summary."), \
             patch.object(p, "ZoteroClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.is_available.return_value = True
            mock_client.get_annotations_for_item.return_value = annotations
            p.scaffold(query="crane", ref=None, force=True, root=Path("."))
        out = notes / "smith-2023-overhead-crane-fault-detection.md"
        self.assertTrue(out.exists())
        content = out.read_text()
        expected = [
            '1. Page 5 (highlight):',
            '   > "important finding"',
            '   *Note: my note*',
            '2. Page 12 (underline):',
            '   > "another point"',
            "<!-- your notes here -->",
        ]
        for line in expected:
            self.assertIn(line, content)

    def test_scaffold_skip_existing(self):
        """Without --force, an existing note is left untouched."""
        from unittest.mock import patch
        from related_work import papers as p

        notes = Path(tempfile.mkdtemp()) / "notes" / "papers"
        notes.mkdir(parents=True, exist_ok=True)
        out = notes / "author-2020-x.md"
        out.write_text("old content\n", encoding="utf-8")
        row = {
            "path": "test.pdf",
            "year": "2020",
            "author": "Test Author",
            "title": "X",
            "zotero_key": "K1",
        }
        with patch.object(p, "NOTES", notes), \
             patch.object(p, "find", return_value=(row, "inv")), \
             patch.object(p, "_extract_paper_body") as extract, \
             patch.object(p, "corpus_root") as corpus_root:
            p.scaffold(query="test", ref=None)
        extract.assert_not_called()
        corpus_root.assert_not_called()
        self.assertEqual(out.read_text(), "old content\n")

    def test_scaffold_missing_zotero_key_shares_snapshot(self):
        from unittest.mock import patch
        from related_work import papers as p

        notes = Path(tempfile.mkdtemp()) / "notes" / "papers"
        row = {
            "path": "test.pdf",
            "year": "2020",
            "author": "Test Author",
            "title": "X",
        }
        snapshot = [{"key": "K1", "data": {"itemType": "journalArticle", "title": "X"}}]
        with patch.object(p, "NOTES", notes), \
             patch.object(p, "find", return_value=(row, "inv")), \
             patch.object(p, "_extract_paper_body", return_value="Summary."), \
             patch.object(p, "corpus_root", return_value=Path(".")), \
             patch.object(p, "ZoteroClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.is_available.return_value = True
            mock_client.get_all_library_items.return_value = snapshot
            mock_client.resolve_item_key.return_value = "K1"
            p.scaffold(query="test", ref=None, force=True)
        mock_client.resolve_item_key.assert_called_once_with(
            path="test.pdf", title="X", items=snapshot
        )
        mock_client.get_annotations_for_item.assert_called_once_with(
            item_key="K1", items=snapshot
        )
        mock_client.get_all_library_items.assert_called_once_with()

    def test_annotations_missing_zotero_key_shares_snapshot(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        from related_work import papers as p

        row = {"path": "test.pdf", "title": "X"}
        snapshot = [{"key": "K1", "data": {"itemType": "journalArticle", "title": "X"}}]
        with patch.object(p, "find", return_value=(row, "inv")), \
             patch("related_work.zotero.ZoteroClient") as mock_client_class, \
             redirect_stdout(StringIO()):
            mock_client = mock_client_class.return_value
            mock_client.is_available.return_value = True
            mock_client.get_all_library_items.return_value = snapshot
            mock_client.resolve_item_key.return_value = "K1"
            p.annotations(query="X", ref=None)
        mock_client.resolve_item_key.assert_called_once_with(
            path="test.pdf", title="X", items=snapshot
        )
        mock_client.get_annotations_for_item.assert_called_once_with(
            item_key="K1", items=snapshot
        )
        mock_client.get_all_library_items.assert_called_once_with()


class TestSlugGeneration(unittest.TestCase):
    """The note filename slug must match existing notes and stay under the cap."""

    def test_empty_inputs(self):
        self.assertEqual(_make_slug("", "2023", "foo"), "unknown-2023-foo")
        self.assertEqual(_make_slug("", "", "foo"), "unknown-foo")
        self.assertEqual(_make_slug("", "", ""), "unknown-untitled")

    def test_surnames_dropped(self):
        self.assertEqual(_make_slug("Alice Smith", "2023", "X"), "smith-2023-x")
        self.assertEqual(
            _make_slug("Corinna Cichy and Stefan Rass", "2019", "An Overview of Data Quality Frameworks"),
            "cichy-rass-2019-an-overview-of-data-quality-frameworks",
        )

    def test_et_al_after_three(self):
        self.assertEqual(_make_slug("a and b and c", "2023", "X"), "a-b-c-2023-x")
        self.assertEqual(_make_slug("a and b and c and d", "2023", "X"), "a-b-et-al-2023-x")

    def test_comma_author(self):
        self.assertEqual(_make_slug("Ni, et al.", "2009", "Sensor network data fault types (ACM TOSN 5(3))"),
                         "ni-et-al-2009-sensor-network-data-fault-types-acm-tosn-5-3")

    def test_subtitle_drop(self):
        self.assertEqual(
            _make_slug("donne and davis", "2026", "robust anomaly detection under contaminated data a comprehensive eval"),
            "donne-davis-2026-robust-anomaly-detection-under-contaminated-data",
        )
        # subtitle kept when it is a large part of a short title
        self.assertEqual(_make_slug("x", "2023", "X a comprehensive evaluation"), "x-2023-x-a-comprehensive-evaluation")

    def test_non_ascii(self):
        self.assertEqual(_make_slug("Donné and Davis", "2026", "X"), "donne-davis-2026-x")
        self.assertEqual(_make_slug("Sondre Sørbø and Massimiliano Ruocco", "2024", "X"), "srb-ruocco-2024-x")

    def test_length_cap(self):
        # Cap lands on a word boundary, not in the middle of a word
        slug = _make_slug(
            "Christoph Scholl and Maximilian Spiegler and Klaus Ludwig and Bjoern M. Eskofier and Andreas Tobola and Dario Zanca",
            "2023", "An Integrated Framework for Data Quality Fusion in Embedded Sensor Systems",
        )
        self.assertLessEqual(len(slug), 90)
        self.assertFalse(slug.endswith("-"))
        self.assertNotIn("embedded-sen", slug)  # not cut mid-word


if __name__ == "__main__":
    unittest.main()
