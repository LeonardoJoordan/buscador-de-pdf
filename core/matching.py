import re
from typing import List, Tuple, Dict, Any, Optional, Set

from rapidfuzz import fuzz

# Identificadores das categorias de qualidade do resultado (cor da borda no QML)
TIER_GREEN = "green"    # frase exata, contígua, dentro de uma única página
TIER_BLUE = "blue"      # frase exata, contígua, mas atravessa a quebra de página
TIER_PURPLE = "purple"  # todas as palavras presentes, porém fora de ordem
TIER_ORANGE = "orange"  # aproximação (fuzzy), abaixo de 100% mas acima do limiar

_TIER_RANK = {TIER_GREEN: 0, TIER_BLUE: 1, TIER_PURPLE: 2, TIER_ORANGE: 3}

_WORD_RE = re.compile(r"\w+", re.UNICODE)

_SNIPPET_WINDOW = 70

# Palavras muito comuns do português (artigos, preposições, conjunções) que,
# sozinhas, aparecem em praticamente qualquer página e por isso são
# ignoradas na checagem de "mesmas palavras, fora de ordem" (tier roxo) —
# do contrário quase todo documento seria classificado como roxo.
_STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "por", "pra", "para", "com", "sem", "sob", "sobre", "entre",
    "e", "ou", "que", "se", "ao", "aos",
    "e", "ser", "foi", "era", "sao", "esta", "estao",
}


def extract_words(normalized_text: str) -> List[str]:
    """Extrai as palavras (tokens) de um texto já normalizado (sem acento/caixa)."""
    return _WORD_RE.findall(normalized_text)


def build_broad_fts_query(words: List[str]) -> Optional[str]:
    """Monta uma consulta FTS5 de recall amplo: qualquer uma das palavras, por prefixo."""
    if not words:
        return None
    return " OR ".join(f"{w}*" for w in words)


def _clean(text: str) -> str:
    return " ".join(text.split())


def _pages_in_range(page_offsets: List[Tuple[int, int, int]], start: int, end: int) -> List[int]:
    """Números de página cujo intervalo [start_char, end_char) intersecta [start, end)."""
    return [
        page_number
        for page_number, p_start, p_end in page_offsets
        if p_start < end and p_end > start
    ]


def _build_span_snippet(original: str, start: int, end: int, window: int = _SNIPPET_WINDOW) -> str:
    s = max(0, start - window)
    e = min(len(original), end + window)
    prefix = "..." if s > 0 else ""
    suffix = "..." if e < len(original) else ""
    before = _clean(original[s:start])
    match = _clean(original[start:end])
    after = _clean(original[end:e])
    return f"{prefix}{before} <b>{match}</b> {after}{suffix}".strip()


def _build_multi_span_snippet(original: str, spans: List[Tuple[int, int]], window: int = _SNIPPET_WINDOW) -> str:
    if not spans:
        return _clean(original[:160])
    spans = sorted(spans)
    center_s = max(0, spans[0][0] - window)
    center_e = min(len(original), spans[-1][1] + window)
    out = []
    cursor = center_s
    for s, e in spans:
        s = max(s, center_s)
        e = min(e, center_e)
        if s < cursor or s >= e:
            continue
        out.append(_clean(original[cursor:s]))
        out.append(f"<b>{_clean(original[s:e])}</b>")
        cursor = e
    out.append(_clean(original[cursor:center_e]))
    prefix = "..." if center_s > 0 else ""
    suffix = "..." if center_e < len(original) else ""
    body = " ".join(p for p in out if p)
    return f"{prefix}{body}{suffix}".strip()


def find_exact_phrase_matches(
    filepath: str,
    original: str,
    normalized: str,
    normalized_query: str,
    page_offsets: List[Tuple[int, int, int]],
    single_word: bool,
    max_matches: int = 20,
) -> Tuple[List[Dict[str, Any]], Set[int]]:
    """
    Localiza ocorrências da frase exata (contígua) no documento.
    Compara palavras completas, ignorando os separadores entre elas.
    """
    results: List[Dict[str, Any]] = []
    claimed: Set[int] = set()
    if not normalized_query:
        return results, claimed

    # Mesma sequência de palavras completas usada na prévia. Separadores
    # (pontuação, espaços e quebras de linha) não mudam a correspondência.
    # A regex mantém os offsets do texto original para o resumo e as páginas.
    words = extract_words(normalized_query)
    if not words:
        return results, claimed
    pattern = re.compile(r"\b" + r"\W+".join(map(re.escape, words)) + r"\b")

    count = 0
    for m in pattern.finditer(normalized):
        if count >= max_matches:
            break
        start, end = m.start(), m.end()
        pages = _pages_in_range(page_offsets, start, end)
        if not pages:
            continue
        tier = TIER_GREEN if len(pages) == 1 else TIER_BLUE
        results.append({
            "filepath": filepath,
            "page_number": pages[0],
            "page_end": pages[-1],
            "matchType": tier,
            "score": 100.0,
            "snippet": _build_span_snippet(original, start, end),
        })
        claimed.update(pages)
        count += 1

    return results, claimed


def find_out_of_order_matches(
    filepath: str,
    original: str,
    normalized: str,
    words: List[str],
    page_offsets: List[Tuple[int, int, int]],
    claimed_pages: Set[int],
) -> List[Dict[str, Any]]:
    """Para páginas ainda não classificadas, verifica se todas as palavras aparecem, fora de ordem."""
    results = []
    significant_words = [w for w in words if w not in _STOPWORDS]
    if len(significant_words) < 2:
        return results

    word_patterns = [re.compile(r"\b" + re.escape(w) + r"\b") for w in significant_words]

    for page_number, p_start, p_end in page_offsets:
        if page_number in claimed_pages:
            continue
        page_norm = normalized[p_start:p_end]
        spans = []
        found_all = True
        for pattern in word_patterns:
            m = pattern.search(page_norm)
            if not m:
                found_all = False
                break
            spans.append((p_start + m.start(), p_start + m.end()))
        if found_all:
            claimed_pages.add(page_number)
            results.append({
                "filepath": filepath,
                "page_number": page_number,
                "page_end": page_number,
                "matchType": TIER_PURPLE,
                "score": 100.0,
                "snippet": _build_multi_span_snippet(original, spans),
            })

    return results


def find_fuzzy_matches(
    filepath: str,
    original: str,
    normalized: str,
    normalized_query: str,
    page_offsets: List[Tuple[int, int, int]],
    claimed_pages: Set[int],
    threshold: float,
) -> List[Dict[str, Any]]:
    """Para páginas ainda não classificadas, calcula similaridade aproximada (rapidfuzz)."""
    results = []
    for page_number, p_start, p_end in page_offsets:
        if page_number in claimed_pages:
            continue
        page_norm = normalized[p_start:p_end]
        if not page_norm.strip():
            continue
        alignment = fuzz.partial_ratio_alignment(normalized_query, page_norm)
        if alignment is None or alignment.score < threshold:
            continue
        start = p_start + alignment.dest_start
        end = p_start + alignment.dest_end
        results.append({
            "filepath": filepath,
            "page_number": page_number,
            "page_end": page_number,
            "matchType": TIER_ORANGE,
            "score": round(alignment.score, 1),
            "snippet": _build_span_snippet(original, start, end),
        })
    return results


def sort_and_limit(results: List[Dict[str, Any]], limit: Optional[int]) -> List[Dict[str, Any]]:
    results.sort(key=lambda r: (_TIER_RANK[r["matchType"]], -r["score"]))
    return results[:limit]
