import unicodedata
from typing import List, Tuple

# Separador usado para unir o texto das páginas em um único bloco por documento.
# Usamos um espaço (e não quebra de linha) porque, na maioria dos PDFs, uma
# frase cortada pela quebra de página é, na verdade, uma frase contínua que
# só "quebrou" visualmente — reconstituir com espaço permite que a busca por
# frase exata funcione mesmo quando ela atravessa a fronteira de página.
# Precisa ser o MESMO valor tanto na extração (indexação nova) quanto na
# migração de bancos antigos, para que os offsets de página fiquem corretos.
PAGE_SEPARATOR = " "


def build_document_text(pages: List[Tuple[int, str]]) -> Tuple[str, List[Tuple[int, int, int]]]:
    """
    Concatena o texto de várias páginas em um único bloco de texto contínuo,
    registrando o offset (em caracteres) onde cada página começa e termina.

    pages: lista de tuplas (page_number, text) já ordenadas por página.
    Retorna: (texto_completo, [(page_number, start_char, end_char), ...])
    """
    parts = []
    offsets = []
    cursor = 0
    total = len(pages)

    for idx, (page_number, text) in enumerate(pages):
        start = cursor
        end = start + len(text)
        offsets.append((page_number, start, end))
        parts.append(text)
        cursor = end
        if idx < total - 1:
            parts.append(PAGE_SEPARATOR)
            cursor += len(PAGE_SEPARATOR)

    return "".join(parts), offsets


def normalize_for_match(text: str) -> str:
    """
    Remove acentuação e converte para minúsculas, preservando o comprimento
    (1 caractere original -> 1 caractere normalizado). Isso é essencial para
    que os offsets de página calculados sobre o texto original continuem
    válidos quando aplicados sobre o texto normalizado (usado para a busca).
    """
    return "".join(unicodedata.normalize("NFKD", ch)[0] for ch in text).lower()
