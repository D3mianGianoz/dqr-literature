"""Minimal sanity suite for the redaction of absolute file paths.

Run from repo root:  python -m scripts.tests.test_paths
Exits 0 if all checks pass, 1 otherwise.
"""
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / "data"
INVENTORY = DATA / "inventory.csv"
SOA = DATA / "soa_citations.csv"
READLOG = DATA / "reading_log.csv"


class TestRedactedPaths(unittest.TestCase):
    """The redaction itself: no secrets, paths are root-relative."""

    def test_no_absolute_or_sensitive_paths(self):
        for p in (INVENTORY, SOA, READLOG):
            text = p.read_text()
            self.assertNotIn("/Users/", text, f"{p.name} still leaks absolute paths")
            self.assertNotIn("Zensor", text, f"{p.name} leaks internal folder structure")

    def test_inventory_paths_are_relative(self):
        for r in csv.DictReader(INVENTORY.open()):
            self.assertTrue(
                r["path"].startswith("Literature/"),
                f"inventory path not relative: {r['path']}",
            )

    def test_soa_local_paths_are_relative(self):
        for r in csv.DictReader(SOA.open()):
            if r.get("local_path"):
                self.assertTrue(
                    r["local_path"].startswith("Literature/"),
                    f"soa local_path not relative: {r['local_path']}",
                )


class TestRowIntegrity(unittest.TestCase):
    """Nothing got lost or corrupted by the redaction."""

    def test_row_counts_stable(self):
        self.assertEqual(385, len(list(csv.DictReader(INVENTORY.open()))))
        self.assertEqual(49, len(list(csv.DictReader(SOA.open()))))
        self.assertEqual(56, len(list(csv.DictReader(READLOG.open()))))

    def test_redaction_preserves_all_rows(self):
        """Non-path columns must be byte-identical to the pre-redaction baseline."""
        baseline = io.StringIO(
            subprocess.check_output(["git", "show", "main:data/inventory.csv"])
            .decode()
        )
        baseline_rows = [
            (r["year"], r["author"], r["title"])
            for r in csv.DictReader(baseline)
        ]
        current_rows = [
            (r["year"], r["author"], r["title"])
            for r in csv.DictReader(INVENTORY.open())
        ]
        self.assertEqual(len(baseline_rows), len(current_rows))
        self.assertEqual(baseline_rows, current_rows)


class TestToolingCompatibility(unittest.TestCase):
    """The tools still find papers by stem; the writer emits relative paths."""

    def test_keys_match_inventory_stems(self):
        inv = {Path(r["path"]).stem for r in csv.DictReader(INVENTORY.open())}
        keys = {r["key"] for r in csv.DictReader(READLOG.open())}
        self.assertTrue(keys.issubset(inv), f"unreadable keys: {keys - inv}")

    def test_soa_stems_resolvable(self):
        inv = {Path(r["path"]).stem: r for r in csv.DictReader(INVENTORY.open())}
        missing = [
            r["ref"]
            for r in csv.DictReader(SOA.open())
            if r.get("local") == "yes"
            and r.get("local_path")
            and Path(r["local_path"]).stem not in inv
        ]
        self.assertEqual([], missing)

    def test_inventory_writer_returns_relative_paths(self):
        tmp = Path(tempfile.mkdtemp())
        lit = tmp / "Literature"
        lit.mkdir(parents=True)
        lit.joinpath("2020 Author Title.pdf").write_text("ok")
        out = tmp / "out.csv"
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.related_work.inventory",
                "--root",
                str(lit),
                "--out",
                str(out),
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        row = next(csv.DictReader(out.open()))
        self.assertEqual(row["path"], "2020 Author Title.pdf")
        self.assertFalse(row["path"].startswith("/"))


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
