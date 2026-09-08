import os
import pymupdf
from typing import Tuple, List, Optional

from core.text_utils import build_document_text


def extract_pdf_data(filepath: str) -> Optional[Tuple[str, str, int, str, List[Tuple[int, int, int]]]]:
    """
    Função 'worker' que abre o PDF e extrai o texto de cada página.
    Retorna: (filepath, filename, total_pages, full_text, page_offsets)
    onde page_offsets é uma lista de (page_number, start_char, end_char)
    indicando em que posição do full_text cada página começa e termina.
    """
    try:
        doc = pymupdf.open(filepath)
        filename = os.path.basename(filepath)
        total_pages = len(doc)
        pages = []

        for page_idx in range(total_pages):
            page = doc[page_idx]
            text = page.get_text("text")  # Extração direta de texto
            # Salva páginas com base 1 para facilitar pro usuário final
            pages.append((page_idx + 1, text))

        doc.close()

        full_text, page_offsets = build_document_text(pages)
        return (filepath, filename, total_pages, full_text, page_offsets)
    except Exception as e:
        print(f"Erro ao ler {filepath}: {e}")
        return None
