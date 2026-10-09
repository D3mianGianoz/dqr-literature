"""Regression checks for the corrections/overrides mechanism."""
import csv, json, sys, contextlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from related_work import inventory

_DATA = Path(__file__).parent.parent / "data"


class TestCorrectionsGuard(unittest.TestCase):
    """The inventory guard must not break mock inventories and must detect drift."""

    def _run(
        self, lit, corr, out, zotero_items=(), zotero_local=False,
        configured_root=None,
    ):
        old_argv = sys.argv
        old_corrections = inventory.CORRECTIONS
        old_configured_root = inventory._pyproject_lit_root
        sys.argv = [old_argv[0]] + (["--zotero-local"] if zotero_local else [])
        inventory.CORRECTIONS = corr
        inventory.INVENTORY = out
        inventory.corpus_root = lambda root=None: lit
        inventory._pyproject_lit_root = lambda: configured_root or lit
        inventory._zotero_items = lambda: list(zotero_items)
        try:
            with contextlib.redirect_stdout(open("/dev/null", "w")), \
                 contextlib.redirect_stderr(open("/dev/null", "w")):
                try:
                    inventory.main()
                    return None
                except SystemExit as e:
                    return str(e)
        finally:
            sys.argv = old_argv
            inventory.CORRECTIONS = old_corrections
            inventory._pyproject_lit_root = old_configured_root

    def test_orphaned_corrections_raise(self):
        """Corrections referencing missing paths are caught."""
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lit = tmp / "Literature"
            lit.mkdir()
            p1 = lit / "2019 Cichy Rass.pdf"
            p1.touch()
            rel1 = p1.relative_to(lit)
            corr = tmp / "corrections.json"
            with open(corr, "w", encoding="utf-8") as fh:
                json.dump({
                    str(rel1): {"year": "2019"},
                    "LITERATURE/Books/Orphan.pdf": {"year": "2020"},
                }, fh)
            msg = self._run(lit, corr, tmp / "out.csv")
            self.assertIsNotNone(msg)
            self.assertIn("references 1 path(s) no longer in the inventory", msg)

    def test_entirely_orphaned_corrections_raise(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lit = tmp / "Literature"
            lit.mkdir()
            (lit / "2020 Current Paper.pdf").touch()
            corr = tmp / "corrections.json"
            corr.write_text(
                json.dumps({"old/removed.pdf": {"year": "2019"}}),
                encoding="utf-8",
            )
            msg = self._run(lit, corr, tmp / "out.csv")
            self.assertIsNotNone(msg)
            self.assertIn("references 1 path(s) no longer in the inventory", msg)

    def test_alternate_root_does_not_validate_configured_corrections(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lit = tmp / "alternate"
            lit.mkdir()
            (lit / "2020 Current Paper.pdf").touch()
            corr = tmp / "corrections.json"
            corr.write_text(
                json.dumps({"old/removed.pdf": {"year": "2019"}}),
                encoding="utf-8",
            )
            msg = self._run(
                lit, corr, tmp / "out.csv", configured_root=tmp / "configured"
            )
            self.assertIsNone(msg)

    def test_malformed_corrections_fail(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lit = tmp / "Literature"
            lit.mkdir()
            corr = tmp / "corrections.json"
            corr.write_text("{", encoding="utf-8")
            msg = self._run(lit, corr, tmp / "out.csv")
            self.assertIsNotNone(msg)
            self.assertIn("Could not load corrections file", msg)

    def test_coverage_after_enrich_raises(self):
        """A row missing both zotero metadata and a correction is caught."""
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lit = tmp / "Literature"
            lit.mkdir()
            p1 = lit / "2019 Cichy Rass.pdf"
            p1.touch()
            p2 = lit / "2020 Foo Bar.pdf"
            p2.touch()
            rel1 = p1.relative_to(lit)
            rel2 = p2.relative_to(lit)
            corr = tmp / "corrections.json"
            with open(corr, "w", encoding="utf-8") as fh:
                json.dump({str(rel1): {"year": "2019"}}, fh)
            msg = self._run(
                lit, corr, tmp / "out.csv",
                zotero_items=[],
                zotero_local=True,
            )
            self.assertIsNotNone(msg)
            self.assertIn("rows lack zotero metadata and a correction", msg)

    def test_stale_corrections_after_enrich_raise(self):
        """A correction still present after Zotero matches its row is caught."""
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lit = tmp / "Literature"
            lit.mkdir()
            p1 = lit / "2019 Cichy Rass.pdf"
            p1.touch()
            p2 = lit / "2020 Foo Bar.pdf"
            p2.touch()
            rel1 = p1.relative_to(lit)
            rel2 = p2.relative_to(lit)
            corr = tmp / "corrections.json"
            with open(corr, "w", encoding="utf-8") as fh:
                json.dump({str(rel1): {"year": "2019"}, str(rel2): {"year": "2020"}}, fh)
            msg = self._run(
                lit, corr, tmp / "out.csv",
                zotero_items=[
                    {
                        "data": {
                            "key": "K1", "itemType": "paper", "title": "Cichy",
                            "creators": [{"creatorType": "author", "name": "Cichy Rass"}],
                            "date": "2019",
                        },
                        "path": str(rel1),
                    },
                    {
                        "data": {
                            "key": "K2", "itemType": "paper", "title": "Foo Bar",
                            "creators": [{"creatorType": "author", "name": "Foo Bar"}],
                            "date": "2020",
                        },
                        "path": str(rel2),
                    },
                ],
                zotero_local=True,
            )
            self.assertIsNotNone(msg)
            self.assertIn("corrections are no longer needed", msg)

    def test_normal_run_with_full_corrections_passes(self):
        """A complete corrections file applies cleanly."""
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lit = tmp / "Literature"
            lit.mkdir()
            p1 = lit / "2019 Cichy Rass.pdf"
            p1.touch()
            rel1 = p1.relative_to(lit)
            corr = tmp / "corrections.json"
            with open(corr, "w", encoding="utf-8") as fh:
                json.dump({str(rel1): {"year": "2019", "author": "Cichy Rass",
                                       "title": "Data Quality Frameworks"}}, fh)
            msg = self._run(lit, corr, tmp / "out.csv")
            self.assertIsNone(msg)
            with open(tmp / "out.csv", encoding="utf-8") as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row["year"], "2019")
            self.assertEqual(row["author"], "Cichy Rass")


if __name__ == "__main__":
    unittest.main()
