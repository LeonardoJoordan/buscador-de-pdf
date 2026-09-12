import os
import tempfile
import unittest

from core.database import DatabaseManager
from core.indexer import scan_folder


class IndexSyncTest(unittest.TestCase):
    def test_scan_separates_pdfs_from_other_files_recursively(self):
        with tempfile.TemporaryDirectory() as directory:
            subfolder = os.path.join(directory, "subpasta")
            os.mkdir(subfolder)
            pdf = os.path.join(directory, "manual.PDF")
            docx = os.path.join(subfolder, "anexo.docx")
            another_docx = os.path.join(directory, "copia.DOCX")
            image = os.path.join(directory, "foto.jpg")
            for path in (pdf, docx, another_docx, image):
                with open(path, "wb"):
                    pass

            pdfs, extensions = scan_folder(directory)

            self.assertEqual([os.path.abspath(pdf)], pdfs)
            self.assertEqual([".docx", ".jpg"], extensions)

    def test_removes_missing_documents_and_keeps_current_ones(self):
        with tempfile.TemporaryDirectory() as directory:
            db = DatabaseManager(os.path.join(directory, "index.db"))
            kept = os.path.join(directory, "mantido.pdf")
            removed = os.path.join(directory, "removido.pdf")
            for path in (kept, removed):
                db.insert_document(path, os.path.basename(path), 1, "conteudo", [(1, 0, 8)])

            db.remove_documents_except([kept])

            self.assertEqual([kept], [item["filepath"] for item in db.get_indexed_files()])
            self.assertEqual([], db.search("conteudo", filepaths=[removed]))

    def test_empty_folder_snapshot_clears_the_index(self):
        with tempfile.TemporaryDirectory() as directory:
            db = DatabaseManager(os.path.join(directory, "index.db"))
            path = os.path.join(directory, "antigo.pdf")
            db.insert_document(path, "antigo.pdf", 1, "conteudo", [(1, 0, 8)])

            db.remove_documents_except([])

            self.assertEqual([], db.get_indexed_files())
            self.assertEqual([], db.search("conteudo"))


if __name__ == "__main__":
    unittest.main()
