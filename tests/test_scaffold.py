import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from related_work import semantic


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
            p.scaffold(query="crane", ref=None, force=True)
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
            p.scaffold(query="crane", ref=None, force=True)
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
        out = notes / "test-author-2020-x.md"
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
             patch.object(p, "_extract_paper_body", return_value="Summary."), \
             patch.object(p, "ZoteroClient") as mock_client_class:
            mock_client_class.return_value.is_available.return_value = False
            p.scaffold(query="test", ref=None)
        self.assertEqual(out.read_text(), "old content\n")


if __name__ == "__main__":
    unittest.main()
