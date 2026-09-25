"""
Verse (poem / song) line detection from PyMuPDF line geometry and fonts.

The book sets verse in an italic face (``Times-Italic``, ``TimesNewRoman,Italic``,
...) and usually indents it well past the body-text left margin (x0 ~150-310 vs.
~88 for text and ~99 for a paragraph indent). A minority of verse — mostly
footnote quotations — is set italic at the margin instead; those lines are short
and come in runs, which distinguishes them from a wrapped italic book title.

Detection must read ``page.get_text("dict")`` span metadata: by the time text is
joined into a paragraph string the font and position of each line are gone.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .models import ExtractorConfig
from .normalizer import TextNormalizer

_LEADING_NUMBER = re.compile(r'^\s*\d')


class VerseDetector:
    """Classifies PDF text lines as verse or not."""

    @staticmethod
    def is_italic_font(font_name: str) -> bool:
        return 'Italic' in font_name or 'Oblique' in font_name

    @classmethod
    def is_verse_font(cls, font_name: str) -> bool:
        """Italic but not bold: bold-italic is used for captions and headings."""
        return cls.is_italic_font(font_name) and 'Bold' not in font_name

    @staticmethod
    def line_text(line: Dict[str, Any]) -> str:
        return ''.join(s['text'] for s in line.get('spans', []))

    @classmethod
    def italic_ratio(cls, line: Dict[str, Any], config: ExtractorConfig) -> float:
        """Share of the line's letters set in an italic font.

        Only non-bold italic counts. Superscript-size spans (footnote markers)
        are ignored, and only letters count, so a roman ``- `` dialogue dash or
        trailing ``, `` doesn't matter.
        """
        italic = total = 0
        for span in line.get('spans', []):
            if span['size'] < config.superscript_max_font_size:
                continue
            letters = sum(1 for c in span['text'] if c.isalpha())
            total += letters
            if cls.is_verse_font(span['font']):
                italic += letters
        return italic / total if total else 0.0

    @classmethod
    def is_candidate(cls, line: Dict[str, Any], config: ExtractorConfig) -> bool:
        """Italic, not an all-caps heading, not a numbered footnote/list entry,
        not a fully parenthesized note such as the ``(Tiếp theo)`` running marker."""
        text = cls.line_text(line).strip()
        if not text or _LEADING_NUMBER.match(text):
            return False
        if text.startswith('(') and text.endswith(')'):
            return False
        if TextNormalizer.is_all_caps(text):
            return False
        return cls.italic_ratio(line, config) >= config.verse_min_italic_ratio

    @classmethod
    def mark_verse_lines(cls, blocks: List[Dict[str, Any]], config: ExtractorConfig) -> None:
        """Set ``line['is_verse']`` on every line of ``blocks`` (in the given order).

        ``blocks`` should already be in reading order. A candidate line is verse
        when indented past ``verse_min_x0``; at the margin it only counts as verse
        inside a run of at least ``verse_margin_min_run`` consecutive short
        (``x1 < verse_margin_max_x1``) candidate lines.
        """
        lines = [line for b in blocks if b.get('type') == 0 for line in b.get('lines', [])]
        margin_run: List[Dict[str, Any]] = []

        def close_run():
            if len(margin_run) >= config.verse_margin_min_run:
                for item in margin_run:
                    item['is_verse'] = True
            margin_run.clear()

        for line in lines:
            line['is_verse'] = False
            if not cls.is_candidate(line, config):
                close_run()
                continue
            x0, _, x1, _ = line['bbox']
            if x0 >= config.verse_min_x0:
                line['is_verse'] = True
                close_run()
            elif x1 < config.verse_margin_max_x1:
                margin_run.append(line)
            else:
                close_run()
        close_run()
