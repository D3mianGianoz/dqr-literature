import tempfile
import unittest
from pathlib import Path

from related_work.semantic import rank_inventory


class TestSemanticRanking(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.inv = self.tmp / "inventory.csv"
        self.readlog = self.tmp / "reading_log.csv"

        # Create mock inventory
        self.inv.write_text(
            "year,author,title,path,zotero_key,abstract\n"
            "2023,Alice Smith,Overhead Crane Sensor Fault Detection and Strain Monitoring,Zpapers/2023/crane.pdf,K1,Monitors industrial crane strain gauges for drift and spikes.\n"
            "2021,Bob Jones,Cooking Recipes with Traditional Italian Pasta,Books/cooking.pdf,K2,A complete guide to boiling pasta and tomato sauce.\n"
            "2022,Carol White,Time Series Anomaly Detection Benchmark in Sensors,Zpapers/2022/benchmark.pdf,K3,Comprehensive evaluation of outlier detectors on sensor time series.\n",
            encoding="utf-8",
        )

        # Mark crane.pdf as read
        self.readlog.write_text(
            "key,source,year,soa_ref,citation\n"
            "crane,inv,2023,,Smith 2023\n",
            encoding="utf-8",
        )

    def test_semantic_ranking_relevance(self):
        results = rank_inventory(
            "crane strain sensor fault",
            unread_only=False,
            inventory_path=self.inv,
            reading_log_path=self.readlog,
        )
        self.assertEqual(len(results), 3)
        # Crane paper should be top ranked
        self.assertEqual(results[0]["key"], "crane")
        # Cooking paper should be last
        self.assertEqual(results[-1]["key"], "cooking")
        self.assertGreater(results[0]["score"], results[-1]["score"])

    def test_unread_filtering(self):
        results = rank_inventory(
            "crane strain sensor fault",
            unread_only=True,
            inventory_path=self.inv,
            reading_log_path=self.readlog,
        )
        # crane is read, so it should be excluded
        keys = [r["key"] for r in results]
        self.assertNotIn("crane", keys)
        self.assertIn("benchmark", keys)
        self.assertIn("cooking", keys)

    def test_cache_save_and_reload(self):
        cache_file = self.tmp / "test_cache.npz"
        self.assertFalse(cache_file.exists())
        # First call writes cache
        results1 = rank_inventory(
            "pasta recipe",
            inventory_path=self.inv,
            reading_log_path=self.readlog,
            cache_path=cache_file,
        )
        self.assertTrue(cache_file.exists())
        # Second call reads from cache
        results2 = rank_inventory(
            "pasta recipe",
            inventory_path=self.inv,
            reading_log_path=self.readlog,
            cache_path=cache_file,
        )
        self.assertEqual(results1[0]["key"], results2[0]["key"])
        self.assertEqual(results1[0]["key"], "cooking")


import subprocess
import sys


class TestPapersCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.inv = self.tmp / "inventory.csv"
        self.readlog = self.tmp / "reading_log.csv"
        self.inv.write_text(
            "year,author,title,path,zotero_key,abstract\n"
            "2023,Alice Smith,Overhead Crane Sensor Fault Detection,Zpapers/2023/crane.pdf,K1,Monitors crane strain gauges.\n",
            encoding="utf-8",
        )
        self.readlog.write_text("key,source,year,soa_ref,citation\n", encoding="utf-8")

    def _run(self, *args: str, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
        import os
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            [sys.executable, "-m", "related_work.papers", *args],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            env=env,
        )

    def test_recommend_outputs_paper(self):
        from unittest.mock import patch
        from related_work import semantic

        with patch.object(semantic, "INVENTORY", self.inv), \
             patch.object(semantic, "READING_LOG", self.readlog):
            results = __import__("related_work.semantic", fromlist=["rank_inventory"]).rank_inventory(
                "crane sensor fault",
                unread_only=True,
                inventory_path=self.inv,
                reading_log_path=self.readlog,
            )
        self.assertTrue(len(results) >= 1)
        self.assertIn("crane", results[0]["key"])

    def test_annotations_no_zotero(self):
        """annotations subcommand exits with an error when Zotero is unavailable."""
        from unittest.mock import patch
        from related_work.zotero import ZoteroClient
        with patch.object(ZoteroClient, "is_available", return_value=False):
            from related_work import papers as papers_mod
            import io
            from contextlib import redirect_stdout
            # Simulate the CLI path: annotations requires Zotero
            with self.assertRaises(SystemExit) as ctx:
                with patch("related_work.papers.find", return_value=({"path": "Zpapers/2023/crane.pdf", "zotero_key": "", "title": "Crane"}, "inv")):
                    papers_mod.annotations(query="crane", ref=None)
            self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
