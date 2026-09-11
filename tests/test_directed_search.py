import os
import tempfile
import time
import unittest

from PySide6.QtCore import QCoreApplication

from bridge import AppBridge
from core.database import DatabaseManager


class DirectedDatabaseTest(unittest.TestCase):
    def test_search_is_limited_to_selected_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            db = DatabaseManager(os.path.join(directory, "index.db"))
            paths = [os.path.join(directory, name) for name in ("a.pdf", "b.pdf", "c.pdf")]
            for path in paths:
                text = "termo presente neste manual"
                db.insert_document(path, os.path.basename(path), 1, text, [(1, 0, len(text))])

            results = db.search("termo presente", filepaths=[paths[0], paths[2]], allow_fuzzy=False)

            self.assertEqual({result["filepath"] for result in results}, {paths[0], paths[2]})
            self.assertEqual(db.search("termo", filepaths=[]), [])


class ImmediateDB:
    def __init__(self):
        self.calls = []

    def get_indexed_files(self):
        return []

    def search(self, query, filepaths=None, **_options):
        self.calls.append((query, filepaths))
        paths = filepaths or ["/manual-a.pdf", "/manual-b.pdf"]
        return [{"filepath": path, "page_number": 1, "query": query} for path in paths]


class DirectedBridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def wait_search(self, bridge):
        deadline = time.monotonic() + 3
        while bridge.isSearching and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertFalse(bridge.isSearching)

    def test_general_state_is_frozen_and_restored(self):
        bridge = AppBridge(ImmediateDB())
        bridge.search("geral")
        self.wait_search(bridge)
        original_results = bridge.searchResults
        self.assertEqual(len(bridge.resultManuals), 2)
        bridge._current_preview_path = "/manual-a.pdf"
        bridge._current_preview_page = 7
        bridge._current_total_pages = 20

        self.assertTrue(bridge.beginDirectedSearch(["/manual-b.pdf"]))
        self.assertTrue(bridge.isDirectedSearch)
        self.assertEqual(bridge.searchResults, [])
        self.assertEqual(len(bridge.resultManuals), 2)
        bridge.search("detalhe")
        self.wait_search(bridge)
        self.assertEqual({item["filepath"] for item in bridge.searchResults}, {"/manual-b.pdf"})
        bridge._current_preview_path = "/manual-b.pdf"
        bridge._current_preview_page = 2

        self.assertTrue(bridge.returnToGeneralSearch())
        self.assertFalse(bridge.isDirectedSearch)
        self.assertEqual(bridge.currentQuery, "geral")
        self.assertEqual(bridge.searchResults, original_results)
        self.assertEqual(bridge.currentFilepath, "/manual-a.pdf")
        self.assertEqual((bridge.currentPage, bridge.currentTotalPages), (7, 20))
        self.assertTrue(bridge.hasSavedDirectedSearch)
        self.assertEqual(bridge.directedFilepaths, ["/manual-b.pdf"])
        self.assertTrue(bridge.beginDirectedSearch(["/manual-b.pdf"]))
        self.assertEqual(bridge.currentQuery, "detalhe")
        self.assertEqual(bridge.currentFilepath, "/manual-b.pdf")
        self.assertEqual(bridge.currentPage, 2)
        self.assertEqual({item["filepath"] for item in bridge.searchResults}, {"/manual-b.pdf"})
        self.assertTrue(bridge.returnToGeneralSearch())
        bridge.search("nova geral")
        self.wait_search(bridge)
        self.assertFalse(bridge.hasSavedDirectedSearch)
        self.assertEqual(bridge.directedFilepaths, [])
        self.assertTrue(bridge.beginDirectedSearch(["/manual-a.pdf"]))
        self.assertEqual(bridge.currentQuery, "")
        self.assertEqual(bridge.searchResults, [])
        bridge.shutdown()

    def test_added_sources_search_again_but_removals_only_filter(self):
        db = ImmediateDB()
        bridge = AppBridge(db)
        try:
            bridge.search("geral")
            self.wait_search(bridge)
            bridge.beginDirectedSearch(["/manual-a.pdf"])
            bridge.search("detalhe")
            self.wait_search(bridge)
            bridge.returnToGeneralSearch()
            calls = len(db.calls)
            bridge.beginDirectedSearch(["/manual-a.pdf", "/manual-b.pdf"])
            self.wait_search(bridge)
            self.assertEqual(len(db.calls), calls + 1)
            self.assertEqual(db.calls[-1], ("detalhe", ["/manual-a.pdf", "/manual-b.pdf"]))
            bridge._current_preview_path = "/manual-a.pdf"
            bridge.returnToGeneralSearch()
            calls = len(db.calls)
            bridge.beginDirectedSearch(["/manual-b.pdf"])
            self.assertFalse(bridge.isSearching)
            self.assertEqual(len(db.calls), calls)
            self.assertEqual([r["filepath"] for r in bridge.searchResults], ["/manual-b.pdf"])
            self.assertEqual(bridge.currentQuery, "detalhe")
            self.assertEqual(bridge.currentFilepath, "")
            bridge.returnToGeneralSearch()
            self.assertFalse(bridge.beginDirectedSearch([]))
            self.assertFalse(bridge.isDirectedSearch)
            bridge.beginDirectedSearch(["/manual-a.pdf"])
            self.wait_search(bridge)
            self.assertEqual(len(db.calls), calls + 1)
            self.assertEqual([r["filepath"] for r in bridge.searchResults], ["/manual-a.pdf"])
        finally:
            bridge.shutdown()


if __name__ == "__main__":
    unittest.main()
