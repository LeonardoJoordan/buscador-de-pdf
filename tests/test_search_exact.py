import unittest
import pymupdf
from core.matching import find_exact_phrase_matches
from core.preview_highlight import classified_highlights
from core.text_utils import normalize_for_match, build_document_text


class ExactSearchTest(unittest.TestCase):
    def test_line_breaks_and_earlier_repeated_word(self):
        text = 'Controle ao Exército. As divisões de\nexército  e inferiores são desempenhadas.'
        query = 'divisões de exército e inferiores são desempenhadas'
        results, _ = find_exact_phrase_matches('x', text, normalize_for_match(text),
            normalize_for_match(query), [(1, 0, len(text))], False)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['matchType'], 'green')
        self.assertIn('<b>divisões de exército e inferiores são desempenhadas</b>', results[0]['snippet'])
        self.assertNotIn('<b>Exército</b>', results[0]['snippet'])

    def test_page_boundary_keeps_correct_offsets(self):
        text, offsets = build_document_text([(1, 'Uma frase\n'), (2, 'exata aqui')])
        results, _ = find_exact_phrase_matches('x', text, normalize_for_match(text),
            'frase exata', offsets, False)
        self.assertEqual(results[0]['matchType'], 'blue')
        self.assertEqual((results[0]['page_number'], results[0]['page_end']), (1, 2))

    def test_preview_and_search_agree_on_word_boundaries_and_separators(self):
        for query, text, expected in [('direito civil', 'direito,\n civil', True),
                                      ('info', 'informacao', False),
                                      ('civil direito', 'direito civil', False)]:
            results, _ = find_exact_phrase_matches('x', text, text, query,
                [(1, 0, len(text))], len(query.split()) == 1)
            import re
            tokens = [(w, pymupdf.Rect(i*10, 0, i*10+9, 10))
                      for i, w in enumerate(re.findall(r'\w+', text))]
            self.assertEqual(bool(results), expected)
            self.assertEqual(bool(classified_highlights(tokens, query, 'exact')), expected)
