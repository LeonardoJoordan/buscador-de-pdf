import os
import tempfile
import unittest

from core.database import DatabaseManager


class SearchCollectionTest(unittest.TestCase):
    def test_search_reaches_every_matching_document_beyond_previous_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            db = DatabaseManager(os.path.join(directory, "index.db"))
            paths = {f"/documentos/{i}.pdf" for i in range(125)}
            for path in paths:
                content = "Uma frase exclusiva para pesquisar."
                db.insert_document(path, os.path.basename(path), 1, content,
                                   [(1, 0, len(content))])

            results = db.search("frase exclusiva", allow_fuzzy=False)

            self.assertEqual({result["filepath"] for result in results}, paths)
            self.assertEqual(len(results), 125)
            self.assertTrue(all(result["matchType"] == "green" for result in results))


if __name__ == "__main__":
    unittest.main()
