"""Destaca o termo buscado sobre a página do PDF na prévia lateral."""

from typing import Any, Iterable, List, Sequence, Tuple

import pymupdf
from rapidfuzz import fuzz

from core.matching import _STOPWORDS, extract_words
from core.text_utils import normalize_for_match

# Amarelo de marca-texto, visível em páginas claras (a maioria dos PDFs).
_HIGHLIGHT_RGB = (1.0, 0.85, 0.15)
_EXACT_RGB = (0.56, 0.93, 0.56)
HIGHLIGHT_MODES = ("all", "exact", "approximate")
_FUZZY_MIN_SCORE = 65.0


def highlight_query_on_page(
    page: pymupdf.Page, query: str, mode: str = "all",
    threshold: float = _FUZZY_MIN_SCORE,
) -> None:
    """Pinta as ocorrências de `query` na página (em memória; não salva o PDF)."""
    query = (query or "").strip()
    if not query:
        return

    tokens = _page_tokens(page)
    highlights = classified_highlights(tokens, query, mode, threshold)
    for rect, kind in highlights:
        color = _EXACT_RGB if kind == "exact" else _HIGHLIGHT_RGB
        if rect.width <= 0 or rect.height <= 0:
            continue
        try:
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=color)
            annot.update()
        except Exception:
            page.draw_rect(
                rect,
                color=None,
                fill=color,
                fill_opacity=0.38,
                width=0,
                overlay=True,
            )


def highlight_rects_from_tokens(
    tokens: Sequence[Tuple[str, Any]], query: str,
    mode: str = "all", threshold: float = _FUZZY_MIN_SCORE,
) -> List[Any]:
    """Compatibilidade para consumidores que precisam apenas dos retângulos."""
    return [rect for rect, _ in classified_highlights(tokens, query, mode, threshold)]


def classified_highlights(tokens, query, mode="all", threshold=_FUZZY_MIN_SCORE):
    """Exatos são palavras completas em sequência, ignorando caixa e acentos.

    As demais palavras da consulta, prefixos e aproximações são amarelos.
    Uma região exata nunca recebe também o destaque aproximado.
    """
    if mode not in HIGHLIGHT_MODES:
        mode = "all"
    words = extract_words(normalize_for_match(query))
    if not words or not tokens:
        return []
    exact = []
    for i in range(len(tokens) - len(words) + 1):
        if all(tokens[i + j][0] == word for j, word in enumerate(words)):
            exact.extend(tokens[i + j][1] for j in range(len(words)))
    exact = _unique_rects(exact)
    exact_keys = {_rect_key(rect) for rect in exact}
    result = [(rect, "exact") for rect in exact] if mode != "approximate" else []
    if mode == "exact":
        return result
    significant = [word for word in words if word not in _STOPWORDS] or words
    others = []
    # Avalia também os intervalos entre ocorrências exatas: a melhor
    # aproximação não deve ser ocultada pela presença de uma frase exata.
    run = []
    for token in list(tokens) + [("", None)]:
        word, rect = token
        if rect is None or _rect_key(rect) in exact_keys:
            if run:
                others.extend(_fuzzy_rects(run, words, threshold))
                run = []
            continue
        run.append(token)
        if any(word == qw or (len(words) == 1 and word.startswith(qw))
               or fuzz.ratio(word, qw) >= threshold for qw in significant):
            others.append(rect)
    result.extend((rect, "approximate") for rect in _unique_rects(others)
                  if _rect_key(rect) not in exact_keys)
    return result


def _page_tokens(page: pymupdf.Page) -> List[Tuple[str, pymupdf.Rect]]:
    tokens: List[Tuple[str, pymupdf.Rect]] = []
    for word in page.get_text("words") or []:
        x0, y0, x1, y1, text = word[:5]
        parts = extract_words(normalize_for_match(str(text)))
        if not parts:
            continue
        rect = pymupdf.Rect(x0, y0, x1, y1)
        for part in parts:
            tokens.append((part, rect))
    return tokens


def _fuzzy_rects(tokens: Sequence[Tuple[str, Any]], q_words: Sequence[str], threshold: float = _FUZZY_MIN_SCORE) -> List[Any]:
    joined_parts: List[str] = []
    spans: List[Tuple[int, int, Any]] = []
    pos = 0
    for i, (tw, rect) in enumerate(tokens):
        if i:
            pos += 1
        spans.append((pos, pos + len(tw), rect))
        pos += len(tw)
        joined_parts.append(tw)

    joined = " ".join(joined_parts)
    query = " ".join(q_words)
    alignment = fuzz.partial_ratio_alignment(query, joined)
    if alignment is None or alignment.score < threshold:
        return []

    start, end = alignment.dest_start, alignment.dest_end
    return [rect for s, e, rect in spans if s < end and e > start]


def _rect_key(rect):
    return tuple(round(float(value), 1) for value in (rect.x0, rect.y0, rect.x1, rect.y1))


def _unique_rects(rects: Iterable[Any]) -> List[Any]:
    unique: List[Any] = []
    seen = set()
    for rect in rects:
        key = (
            round(float(rect.x0), 1),
            round(float(rect.y0), 1),
            round(float(rect.x1), 1),
            round(float(rect.y1), 1),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(rect)
    return unique
