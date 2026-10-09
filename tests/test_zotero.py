import unittest
from unittest.mock import MagicMock, patch

from related_work.zotero import ZoteroClient


class TestZoteroClient(unittest.TestCase):
    def test_offline_graceful_handling(self):
        client = ZoteroClient(base_url="http://127.0.0.1:99999/api")
        self.assertFalse(client.is_available())
        self.assertEqual(client.get_collections(), {})
        self.assertEqual(client.get_annotations_for_item("NOKEY"), [])

    @patch.object(ZoteroClient, "_request")
    def test_collection_path_resolution(self, mock_request):
        mock_request.return_value = [
            {"key": "C1", "data": {"name": "PhD", "parentCollection": False}},
            {"key": "C2", "data": {"name": "family", "parentCollection": "C1"}},
            {"key": "C3", "data": {"name": "reconstruction", "parentCollection": "C2"}},
        ]
        client = ZoteroClient()
        collections = client.get_collections()
        self.assertIn("C3", collections)
        self.assertEqual(collections["C3"]["path"], "PhD/family/reconstruction")
        self.assertEqual(collections["C1"]["path"], "PhD")

    @patch.object(ZoteroClient, "get_all_library_items")
    def test_resolve_item_key_by_attachment_and_title(self, mock_items):
        mock_items.return_value = [
            {
                "key": "TOP1",
                "data": {
                    "itemType": "journalArticle",
                    "title": "Robust Anomaly Detection Under Contaminated Data: A Comprehensive Evaluation",
                },
            },
            {
                "key": "ATT1",
                "data": {
                    "itemType": "attachment",
                    "parentItem": "TOP1",
                    "filename": "donne_and_davis_2026_robust_anomaly_detection.pdf",
                },
            },
        ]
        client = ZoteroClient()
        # Direct key
        self.assertEqual(client.resolve_item_key(zotero_key="TOP1"), "TOP1")
        # Match via attachment filename
        self.assertEqual(
            client.resolve_item_key(path="some/folder/donne_and_davis_2026_robust_anomaly_detection.pdf"),
            "TOP1",
        )
        # Match via title
        self.assertEqual(
            client.resolve_item_key(title="Robust Anomaly Detection Under Contaminated Data"),
            "TOP1",
        )


    @patch.object(ZoteroClient, "get_all_library_items")
    def test_get_annotations_by_top_item(self, mock_items):
        """Annotations are correctly linked through attachments to their top-level item."""
        mock_items.return_value = [
            {"key": "TOP1", "data": {"itemType": "journalArticle", "title": "Crane Study"}},
            {"key": "ATT1", "data": {"itemType": "attachment", "parentItem": "TOP1", "filename": "crane.pdf"}},
            {
                "key": "ANN1",
                "data": {
                    "itemType": "annotation",
                    "parentItem": "ATT1",
                    "annotationText": "sensor fault",
                    "annotationComment": "important",
                    "annotationPageLabel": "3",
                    "annotationType": "highlight",
                    "annotationColor": "#ffff00",
                    "dateModified": "2024-01-01",
                },
            },
            # Annotation with no matching attachment parent -> should be dropped
            {
                "key": "ANN2",
                "data": {
                    "itemType": "annotation",
                    "parentItem": "ORPHAN",
                    "annotationText": "orphaned",
                    "annotationComment": "",
                    "annotationPageLabel": "1",
                    "annotationType": "underline",
                    "annotationColor": "",
                    "dateModified": "",
                },
            },
        ]
        client = ZoteroClient()
        result = client.get_annotations_by_top_item()
        self.assertIn("TOP1", result)
        self.assertNotIn("ORPHAN", result)
        ann = result["TOP1"][0]
        self.assertEqual(ann["text"], "sensor fault")
        self.assertEqual(ann["page"], "3")
        self.assertEqual(ann["type"], "highlight")

    @patch.object(ZoteroClient, "get_all_library_items")
    def test_get_annotations_for_item_single_fetch(self, mock_items):
        """get_annotations_for_item with a direct key fetches the library exactly once
        (not twice as before). No redundant resolve_item_key lookup."""
        mock_items.return_value = []
        client = ZoteroClient()
        # Providing item_key directly skips the resolve_item_key fetch;
        # get_annotations_by_top_item still needs one fetch.
        result = client.get_annotations_for_item(item_key="SOMEKEY")
        mock_items.assert_called_once()
        self.assertEqual(result, [])

    @patch.object(ZoteroClient, "get_all_library_items")
    def test_get_annotations_for_item_reuses_supplied_snapshot(self, mock_items):
        snapshot = [
            {"key": "TOP1", "data": {"itemType": "journalArticle", "title": "Crane Study"}},
            {"key": "ATT1", "data": {"itemType": "attachment", "parentItem": "TOP1", "filename": "crane.pdf"}},
        ]
        mock_items.return_value = snapshot
        client = ZoteroClient()
        items = client.get_all_library_items()
        key = client.resolve_item_key(path="crane.pdf", items=items)

        self.assertEqual(client.get_annotations_for_item(item_key=key, items=items), [])
        mock_items.assert_called_once()


if __name__ == "__main__":
    unittest.main()
