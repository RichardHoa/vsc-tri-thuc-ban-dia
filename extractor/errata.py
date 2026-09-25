"""
Known Source Errata — corrections for errors printed in data.pdf itself.

Each entry is a deliberate, page-scoped exception: the textbook is wrong (or
mistypeset) at that exact spot and the extractor repairs it for the reader.
Entries are literal ``(find, replace)`` pairs applied to one body line's
normalized text, only on the listed 1-based page — never book-wide heuristics.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

#: page -> [(find, replace), ...]
PAGE_TEXT_FIXES: Dict[int, List[Tuple[str, str]]] = {
    # Story 91 (BÀ LỚN ĐƯỜI ƯƠI): the footnote-1 marker after "đười ươi" is
    # typeset full-size (11.7pt) instead of superscript, so it reads as a
    # literal "1". Restore it as the [^1] footnote marker.
    560: [("con đười ươi1.", "con đười ươi[^1].")],
}


def apply_page_text_fixes(page_num: int, text: str) -> str:
    """Apply this page's literal fixes to ``text`` (a normalized body line)."""
    for find, replace in PAGE_TEXT_FIXES.get(page_num, []):
        text = text.replace(find, replace)
    return text
