import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from PySide6.QtGui import QImage
from core.preview_cache import PreviewCache


class PreviewCacheTests(unittest.TestCase):
    def test_window_edges(self):
        self.assertEqual(PreviewCache.neighbors(1, 8), [2, 3, 4])
        self.assertEqual(PreviewCache.neighbors(5, 8), [6, 4, 7, 3, 8])
        self.assertEqual(PreviewCache.neighbors(8, 8), [7, 6])

    def test_memory_limit_preserves_current_page(self):
        image = QImage(100, 100, QImage.Format_RGB888)
        cache = PreviewCache(max_bytes=image.sizeInBytes() * 2)
        cache._page = 4
        cache._put('ctx', 4, image, 10)
        cache._put('ctx', 5, image, 10)
        cache._put('ctx', 7, image, 10)
        self.assertEqual(set(cache._images), {('ctx', 4), ('ctx', 5)})
        self.assertLessEqual(cache._bytes, cache.max_bytes)
        cache.close()

    def test_prefetch_reuse_and_invalidation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'sample.pdf')
            with pymupdf.open() as doc:
                for i in range(8):
                    page = doc.new_page(width=150, height=150)
                    page.insert_text((15, 30), f'Page {i + 1} casa casas')
                doc.save(path)
            cache = PreviewCache()
            try:
                first = cache.get(path, 4, 'casa', 'exact')
                self.assertFalse(first.isNull())
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    with cache._condition:
                        if len(cache._images) == 6:
                            break
                    time.sleep(.05)
                with cache._condition:
                    self.assertEqual({key[1] for key in cache._images}, {2, 3, 4, 5, 6, 7})
                with patch('core.preview_cache.render_page', side_effect=AssertionError('Cache miss')):
                    self.assertFalse(cache.get(path, 5, 'casa', 'exact').isNull())
                cache.get(path, 1, 'casas', 'approximate')
                with cache._condition:
                    self.assertTrue(all(key[0][3:5] == ('casas', 'approximate') for key in cache._images))
                    self.assertTrue(all(1 <= key[1] <= 4 for key in cache._images))
            finally:
                cache.close()
            self.assertFalse(cache._thread.is_alive())


if __name__ == '__main__':
    unittest.main()
