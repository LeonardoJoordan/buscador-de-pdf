import threading
import time
import unittest
from PySide6.QtCore import QCoreApplication, QTimer
from bridge import AppBridge


class FakeDB:
    def __init__(self):
        self.release = threading.Event()
        self.started = threading.Event()
        self.fail = False
        self.thread = None

    def get_indexed_files(self):
        return []

    def search(self, query, cancelled=None, **options):
        self.thread = threading.get_ident()
        self.started.set()
        while not self.release.wait(0.01):
            if cancelled():
                return []
        if self.fail:
            raise RuntimeError('falha simulada')
        return [{'query': query}]


class AsyncSearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def pump_until(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertTrue(predicate())

    def test_responsive_snapshot_duplicate_guard_and_error_recovery(self):
        db = FakeDB()
        bridge = AppBridge(db)
        try:
            bridge._search_results = [{'query': 'anterior'}]
            bridge._last_query = 'anterior'
            bridge.search('nova')
            self.assertTrue(bridge.isSearching)
            bridge.search('ignorada')
            ticks = []
            QTimer.singleShot(0, lambda: ticks.append(True))
            self.pump_until(lambda: ticks and db.started.is_set())
            self.assertNotEqual(db.thread, threading.get_ident())
            self.assertEqual(bridge._last_query, 'anterior')
            self.assertEqual(bridge.searchResults, [{'query': 'anterior'}])
            db.release.set()
            self.pump_until(lambda: not bridge.isSearching)
            self.assertEqual(bridge.searchResults, [{'query': 'nova'}])
            db.fail = True
            bridge.search('falha')
            self.pump_until(lambda: not bridge.isSearching)
            self.assertIn('falha simulada', bridge.searchError)
            self.assertEqual(bridge._last_query, 'nova')
            db.fail = False
            bridge.search('recuperada')
            self.pump_until(lambda: not bridge.isSearching)
            self.assertFalse(bridge.searchError)
        finally:
            db.release.set()
            bridge.shutdown()

    def test_shutdown_interrupts_and_joins_search(self):
        db = FakeDB()
        bridge = AppBridge(db)
        bridge.search('consulta')
        bridge.shutdown()
        self.assertFalse(bridge._search_worker.isRunning())
        self.app.processEvents()
