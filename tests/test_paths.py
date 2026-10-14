"""Minimal sanity suite for the redaction of absolute file paths.

Run from repo root:  uv run python -m unittest discover -s tests
Exits 0 if all checks pass, 1 otherwise.
"""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
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
        with INVENTORY.open() as stream:
            for row in csv.DictReader(stream):
                path = Path(row["path"])
                self.assertFalse(
                    path.is_absolute() or ".." in path.parts,
                    f"inventory path is not safely relative: {row['path']}",
                )


class TestRowIntegrity(unittest.TestCase):
    """Nothing got lost or corrupted by the redaction."""

    def test_inventory_has_rows_and_soa_has_rows(self):
        # Exact totals are snapshots that change as the collection grows;
        # assert valid headers, non-empty files, and a representative sample.
        for path, fieldnames in (
            (INVENTORY, ["year", "author", "title", "path", "zotero_key", "abstract"]),
            (SOA, ["ref", "year", "surnames", "local", "method", "local_path", "citation"]),
        ):
            with path.open() as stream:
                reader = csv.DictReader(stream)
                rows = list(reader)
                self.assertEqual(reader.fieldnames, fieldnames, f"{path} header")
                self.assertGreater(len(rows), 0, f"{path} is empty")
        with READLOG.open() as stream:
            rows = list(csv.DictReader(stream))
            self.assertGreater(len(rows), 0, "reading_log is empty")
            self.assertEqual(
                {"key", "source", "year", "soa_ref", "citation"},
                set(rows[0].keys()),
            )
        # Regression guard: a couple of known inventory paths are still indexed.
        with INVENTORY.open() as stream:
            inv = {row["path"] for row in csv.DictReader(stream)}
        known = {
            "Books/Charu C. Aggarwal - Outlier Analysis.pdf",
            "Books/Data-Mining.-Concepts-and-Techniques-4th-Edition-Morgan-Kaufmann-2022-Han-Pei-Tong.pdf",
        }
        self.assertTrue(known.issubset(inv), f"missing known rows: {known - inv}")


class TestToolingCompatibility(unittest.TestCase):
    """The tools still find papers by stem; the writer emits relative paths."""

    def test_keys_match_inventory_stems(self):
        with INVENTORY.open() as stream:
            inv = {Path(row["path"]).stem for row in csv.DictReader(stream)}
        with READLOG.open() as stream:
            keys = {row["key"] for row in csv.DictReader(stream)}
        self.assertTrue(keys.issubset(inv), f"unreadable keys: {keys - inv}")

    def test_soa_stems_resolvable(self):
        with INVENTORY.open() as stream:
            inv = {
                Path(row["path"]).stem: row for row in csv.DictReader(stream)
            }
        with SOA.open() as stream:
            missing = [
                row["ref"]
                for row in csv.DictReader(stream)
                if row.get("local") == "yes"
                and row.get("local_path")
                and Path(row["local_path"]).stem not in inv
            ]
        self.assertEqual([], missing)

    def test_historical_soa_paths_resolve_from_literature_root(self):
        from related_work.config import inventory_path

        with INVENTORY.open() as stream:
            inventory_paths = {row["path"] for row in csv.DictReader(stream)}
        with SOA.open() as stream:
            local_paths = [
                row["local_path"]
                for row in csv.DictReader(stream)
                if row.get("local") == "yes" and row.get("local_path")
            ]
        self.assertTrue(local_paths)
        self.assertTrue(all(inventory_path(path) in inventory_paths for path in local_paths))

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
                "related_work.inventory",
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
        with out.open() as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual(
            list(row),
            ["year", "author", "title", "path", "zotero_key", "abstract"],
        )
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
        from related_work.match_refs import entries
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
        from related_work.match_refs import _surname_ner
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
        from related_work.match_refs import entries, match
        with (REPO / "data/inventory.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        text = """Bibliography
[1] Richard Y. Wang and Diane M. Strong. Beyond Accuracy: What Data Quality Means to Data Consumers. Journal of Management Information Systems, 12(4):5\u201333, March 1996.
"""
        d = entries(text)
        hit, method = match(d["1"], rows)
        self.assertEqual(method, "exact")
        self.assertEqual(Path(hit["path"]).stem, "Wang_Strong_1996_Beyond_Accuracy")

    def test_extract_abstract(self):
        from related_work.papers import _extract_abstract
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
        from related_work.papers import _extract_abstract
        sentences = [
            "This paper studies anomaly detection.",
            "We propose a baseline.",
            "Results follow.",
            "1 Introduction: Background follows.",
        ]
        self.assertEqual(_extract_abstract(sentences), [])

    def test_extractive_summary(self):
        import spacy
        from related_work.papers import _extractive_summary
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
        from related_work.papers import show
        fake_row = {"path": "tests/assets/test_abstract.pdf", "year": "2025"}
        with unittest.mock.patch("related_work.papers.find", return_value=(fake_row, "test")):
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
        from related_work.papers import show
        pdf_path = REPO / "tests/assets/test_no_abstract.pdf"
        fake_row = {"path": str(pdf_path), "year": "2025"}
        with unittest.mock.patch("related_work.papers.find", return_value=(fake_row, "test")):
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

    def test_notes_readme_links_resolve(self):
        import re
        readme = REPO / "notes/README.md"
        self.assertTrue(readme.exists())
        content = readme.read_text(encoding="utf-8")
        links = re.findall(r"\(([^)]+\.md)\)", content)
        self.assertGreater(len(links), 0)
        for link in links:
            target = (REPO / "notes" / link).resolve()
            self.assertTrue(target.exists(), f"Broken link in notes/README.md: {link}")

    def test_match_refs_empty_bibliography_creates_valid_csv(self):
        tmp = Path(tempfile.mkdtemp())
        empty_refs = tmp / "empty_refs.txt"
        empty_refs.write_text("", encoding="utf-8")
        out_csv = tmp / "out.csv"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "related_work.match_refs",
                "--refs",
                str(empty_refs),
                "--out",
                str(out_csv),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"match_refs failed: {proc.stderr}")
        self.assertTrue(out_csv.exists())
        with out_csv.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            self.assertEqual(
                reader.fieldnames,
                ["ref", "year", "surnames", "local", "method", "local_path", "citation"],
            )
            self.assertEqual(list(reader), [])


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
