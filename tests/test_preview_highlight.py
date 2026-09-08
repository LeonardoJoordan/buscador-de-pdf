import unittest
import pymupdf
from core.preview_highlight import classified_highlights, highlight_query_on_page


def tokens(text):
    return [(word, pymupdf.Rect(i * 20, 0, i * 20 + 18, 10))
            for i, word in enumerate(text.split())]


class HighlightsTest(unittest.TestCase):
    def test_exact_does_not_match_prefix_or_reordered_phrase(self):
        self.assertEqual(classified_highlights(tokens('informacao'), 'info', 'exact'), [])
        self.assertEqual(classified_highlights(tokens('civil direito'), 'direito civil', 'exact'), [])

    def test_exact_and_other_occurrences_coexist(self):
        hits = classified_highlights(tokens('direito civil civil direito'), 'direito civil')
        self.assertEqual([kind for _, kind in hits], ['exact', 'exact', 'approximate', 'approximate'])

    def test_approximate_excludes_exact(self):
        hits = classified_highlights(tokens('casa casas caza'), 'casa', 'approximate')
        self.assertEqual(len(hits), 2)
        self.assertTrue(all(kind == 'approximate' for _, kind in hits))

    def test_threshold(self):
        self.assertEqual(classified_highlights(tokens('caza'), 'casa', threshold=95), [])
        self.assertEqual(len(classified_highlights(tokens('caza'), 'casa', threshold=65)), 1)

    def test_accents_case_and_repeated_matches(self):
        hits = classified_highlights(tokens('acao acao'), 'AÇÃO', 'exact')
        self.assertEqual(len(hits), 2)

    def test_real_pdf_colors_and_no_disk_mutation(self):
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((50, 50), 'casa casas')
            highlight_query_on_page(page, 'casa')
            colors = [annot.colors['stroke'] for annot in page.annots()]
            self.assertEqual(len(colors), 2)
            self.assertGreater(colors[0][1], colors[0][0])
            self.assertGreater(colors[1][0], colors[1][1])


if __name__ == '__main__':
    unittest.main()
