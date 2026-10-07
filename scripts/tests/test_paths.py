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


class TestSpacyRelatedWork(unittest.TestCase):
    """spaCy-powered features added by the feat/spacy-matching plan.

    Skipped entirely when the model cannot be loaded (no graceful fallback).
    """

    @classmethod
    def setUpClass(cls):
        try:
            import spacy  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("spaCy not installed")
        try:
            import spacy
            spacy.load("en_core_web_md")
        except OSError:
            raise unittest.SkipTest("en_core_web_md model not installed")

    def test_ner_surname_extraction(self):
        from scripts.related_work.match_refs import entries
        text = """Bibliography
[1] Richard Y. Wang and Diane M. Strong. Beyond Accuracy: What Data Quality Means to Data Consumers. Journal of Management Information Systems, 12(4):5\u201333, March 1996.
[2] Guansong Pang, Chunhua Shen, Longbing Cao, and Anton Van Den Hengel. Deep Learning for Anomaly Detection: A Review. ACM Computing Surveys, 41(3):1\u201358, July 2009.
[3] V. Barnett and T. Lewis. Outliers in Statistical Data. J. Wiley & Sons, 1994.
"""
        d = entries(text)
        self.assertEqual(d["1"][1], ["wang", "strong"])
        self.assertEqual(d["2"][1], ["pang", "shen", "cao", "hengel"])
        self.assertEqual(d["3"][1], ["barnett", "lewis"])

    def test_ner_hyphenated_and_hybrid_surname(self):
        from scripts.related_work.match_refs import _surname_ner
        self.assertEqual(
            _surname_ner("Sahand Hariri, Matias Carrasco Kind, and Robert J. Brunner"),
            ["hariri", "kind", "brunner"],
        )
        self.assertEqual(
            _surname_ner("M. Mourad and J.-L. Bertrand-Krajewski"),
            ["mourad", "bertrand-krajewski"],
        )

    def test_similarity_exact_promotion(self):
        import csv
        from pathlib import Path
        from scripts.related_work.match_refs import entries, match
        rows = list(csv.DictReader((REPO / "data/inventory.csv").open()))
        text = """Bibliography
[1] Richard Y. Wang and Diane M. Strong. Beyond Accuracy: What Data Quality Means to Data Consumers. Journal of Management Information Systems, 12(4):5\u201333, March 1996.
"""
        d = entries(text)
        hit, method = match(d["1"], rows)
        self.assertEqual(method, "exact")
        self.assertEqual(Path(hit["path"]).stem, "Wang_Strong_1996_Beyond_Accuracy")

    def test_extract_abstract(self):
        from scripts.related_work.papers import _extract_abstract
        sentences = [
            "Test Paper Title",
            "Authors A. B. C.",
            "Abstract: This paper studies anomaly detection in streaming sensor data.",
            "We propose a simple baseline and compare it against existing methods.",
            "Our results show improvements over the state of the art.",
            "Introduction: Background and motivation for the study follow here.",
        ]
        abstract = _extract_abstract(sentences)
        self.assertEqual(len(abstract), 3)
        self.assertEqual(
            abstract[0],
            "Abstract: This paper studies anomaly detection in streaming sensor data.",
        )

    def test_extract_abstract_no_heading(self):
        from scripts.related_work.papers import _extract_abstract
        sentences = [
            "This paper studies anomaly detection.",
            "We propose a baseline.",
            "Results follow.",
            "1 Introduction: Background follows.",
        ]
        self.assertEqual(_extract_abstract(sentences), [])

    def test_extractive_summary(self):
        import spacy
        from scripts.related_work.papers import _extractive_summary
        nlp = spacy.load("en_core_web_md")
        text = (
            "Anomaly detection is studied in this work. "
            "The first sentence should be important. "
            "We propose a simple baseline and compare it against existing methods. "
            "Results are presented in the second section. Introduction follows."
        )
        doc = nlp(text)
        summary = _extractive_summary(doc, 3)
        self.assertEqual(len(summary), 3)
        joined = " ".join(summary).lower()
        self.assertTrue("anomaly" in joined or "baseline" in joined)

    def test_show_abstract_from_pdf(self):
        import io
        import sys
        import unittest.mock
        from scripts.related_work.papers import show
        fake_row = {"path": "scripts/tests/assets/test_abstract.pdf", "year": "2025"}
        with unittest.mock.patch("scripts.related_work.papers.find", return_value=(fake_row, "test")):
            out = io.StringIO()
            old = sys.stdout
            sys.stdout = out
            try:
                show("test", None, 1000, REPO)
            finally:
                sys.stdout = old
        body = out.getvalue()
        self.assertIn("anomaly detection", body.lower())

    def test_show_fallback_summary(self):
        import io
        import sys
        import unittest.mock
        from scripts.related_work.papers import show
        pdf_path = REPO / "scripts/tests/assets/test_no_abstract.pdf"
        fake_row = {"path": str(pdf_path), "year": "2025"}
        with unittest.mock.patch("scripts.related_work.papers.find", return_value=(fake_row, "test")):
            out = io.StringIO()
            old = sys.stdout
            sys.stdout = out
            try:
                show("test", None, 1000)
            finally:
                sys.stdout = old
        body = out.getvalue()
        # fallback summary should contain something about anomaly detection
        self.assertIn("anomaly", body.lower())


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
