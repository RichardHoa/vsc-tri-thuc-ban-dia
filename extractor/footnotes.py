"""
Footnote Parsing, Re-indexing, and Extraction Engine.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
import fitz  # PyMuPDF

from .models import ExtractorConfig, Footnote, Paragraph, Verse
from .normalizer import TextNormalizer
from .geometry import PdfGeometryHelper
from .verse import VerseDetector


class FootnoteEngine:
    """Parses, re-indexes, and formats footnotes."""

    # "N. Text" / "N Text", or a number glued straight onto a capitalised word
    # ("2Theo ..." on page 536) — never a number glued to digits (years). The
    # preceding space is a lookbehind, not consumed, so an empty footnote
    # ("1 2 Theo ..." on page 601) doesn't swallow the next number.
    FOOTNOTE_SPLIT_PAT = re.compile(
        r'(?:^|(?<=\s))(\d+)(?:[\.\s]+(?=[A-ZÀ-Ỵ\"\'“‘\(\[\d])|(?=[A-ZÀ-Ỵ]))'
    )

    @classmethod
    def parse_footnote_text(cls, text: str, page_num: int) -> List[Dict[str, any]]:
        """
        Splits footnote block text into individual footnote entries.
        Supports single and sequential multi-footnote blocks (e.g. 1. ... 2. ...).

        Text before the first footnote number is a footnote carried over from the
        previous page: it is returned as a leading entry with ``continued=True``
        (its ``orig_num`` is resolved by the caller, which knows that page).
        """
        text = TextNormalizer.clean_spaces(text)
        if not text:
            return []

        # Fix OCR scanning artifact like '11.' for '1.' at start
        text = re.sub(r'^11\.\s*', '1. ', text)

        valid_splits = []
        expected_num = 1

        for match in cls.FOOTNOTE_SPLIT_PAT.finditer(text):
            digits = match.group(1)
            # The PDF sometimes prints a footnote number doubled ("33" for 3,
            # "11" for 1 — pages 607, 609-612); the body marker is the single one.
            if int(digits) == expected_num or digits == str(expected_num) * 2:
                valid_splits.append((expected_num, match.start(1), match.end()))
                expected_num += 1

        if not valid_splits:
            m0 = re.match(r'^(\d+)(?:[\.\s]+|(?=[A-ZÀ-Ỵ]))', text)
            if m0:
                content = TextNormalizer.clean_spaces(text[m0.end():])
                return [{'orig_num': int(m0.group(1)), 'page': page_num, 'text': content,
                         'continued': False}]
            return [{'orig_num': 1, 'page': page_num, 'text': TextNormalizer.clean_spaces(text),
                     'continued': True}]

        items = []
        head = TextNormalizer.clean_spaces(text[:valid_splits[0][1]])
        if head:
            items.append({'orig_num': 1, 'page': page_num, 'text': head, 'continued': True})
        for i, (num, _, start_content) in enumerate(valid_splits):
            end_content = valid_splits[i + 1][1] if i + 1 < len(valid_splits) else len(text)
            content = TextNormalizer.clean_spaces(text[start_content:end_content])
            content = re.sub(r'^[\.\-\s]+', '', content)
            items.append({
                'orig_num': num,
                'page': page_num,
                'text': content,
                'continued': False
            })

        return items

    @staticmethod
    def footer_lines(page: fitz.Page, config: ExtractorConfig) -> List[Dict[str, Any]]:
        """Footnote-region lines of ``page`` in reading order, each tagged ``is_verse``."""
        h_sep_y = PdfGeometryHelper.find_footer_separator_y(page)
        blocks = [b for b in page.get_text('dict').get('blocks', []) if b.get('type') == 0]
        blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))
        VerseDetector.mark_verse_lines(blocks, config)

        lines: List[Dict[str, Any]] = []
        for b in blocks:
            for l in b.get('lines', []):
                y0 = l['bbox'][1]
                raw_line = ''.join(s['text'] for s in l.get('spans', [])).strip()
                if not raw_line:
                    continue
                if PdfGeometryHelper.is_footer_line(
                    y0, raw_line, h_sep_y, config.max_footer_y, config.footer_fallback_y
                ) and y0 <= config.max_footer_y:
                    lines.append(l)
        return lines

    @classmethod
    def page_entries(cls, doc: fitz.Document, page_num: int, config: ExtractorConfig) -> List[Dict[str, Any]]:
        """Parsed footnote entries of one page (1-based), plus its verse lines.

        Each entry dict gains ``verse_lines`` (the page's verse lines, shared)
        so callers can rebuild verse parts; an empty list means no footnotes.
        """
        if page_num < 1 or page_num > len(doc):
            return []
        fn_lines = cls.footer_lines(doc[page_num - 1], config)
        if not fn_lines:
            return []
        raw_lines = [''.join(s['text'] for s in l['spans']).strip() for l in fn_lines]
        combined_fn_text = ' '.join(TextNormalizer.normalize_encoding(line) for line in raw_lines)
        entries = cls.parse_footnote_text(combined_fn_text, page_num)
        if not entries and combined_fn_text.strip():
            entries = [{'orig_num': 1, 'page': page_num,
                        'text': TextNormalizer.clean_spaces(combined_fn_text), 'continued': True}]
        verse_lines = [
            TextNormalizer.clean_spaces(TextNormalizer.normalize_encoding(raw))
            for raw, l in zip(raw_lines, fn_lines) if l.get('is_verse')
        ]
        for entry in entries:
            entry['verse_lines'] = verse_lines
        return entries

    @classmethod
    def last_footnote_num(cls, doc: fitz.Document, page_num: int, config: ExtractorConfig,
                          max_back: int = 10) -> Optional[int]:
        """Number of the footnote still open at the bottom of ``page_num``.

        That is the page's last numbered entry, or — when the page's footnote area
        is entirely a continuation — the number it inherits from earlier pages.
        ``None`` when the page has no footnotes.
        """
        entries = cls.page_entries(doc, page_num, config)
        if not entries:
            return None
        numbered = [e for e in entries if not e['continued']]
        if numbered:
            return numbered[-1]['orig_num']
        if max_back <= 0:
            return None
        return cls.last_footnote_num(doc, page_num - 1, config, max_back - 1)

    @staticmethod
    def split_verse_parts(entries: List[Dict[str, Any]], verse_lines: List[str]) -> List[List[Paragraph]]:
        """Split each entry's text into prose / ``Verse`` parts.

        Verse lines are matched in order against the entries' text; an entry
        without verse gets an empty list (render ``text`` as-is).
        """
        all_parts: List[List[Paragraph]] = []
        k = 0
        for entry in entries:
            text = entry['text']
            parts: List[Paragraph] = []
            pos = 0
            found = False
            while k < len(verse_lines):
                idx = text.find(verse_lines[k], pos) if verse_lines[k] else -1
                if idx < 0:
                    break
                found = True
                prose = text[pos:idx].strip()
                if prose:
                    parts.append(prose)
                if parts and isinstance(parts[-1], Verse):
                    parts[-1].lines.append(verse_lines[k])
                else:
                    parts.append(Verse([verse_lines[k]]))
                pos = idx + len(verse_lines[k])
                k += 1
            if found:
                tail = text[pos:].strip()
                if tail:
                    parts.append(tail)
            all_parts.append(parts if found else [])
        return all_parts

    @classmethod
    def collect_story_footnotes(
        cls,
        doc: fitz.Document,
        start_page: int,
        end_page: int,
        config: ExtractorConfig
    ) -> Tuple[Dict[int, List[Footnote]], List[Footnote]]:
        """
        Scans story pages to extract footnotes and preserves original page-level footnote IDs.

        The unnumbered head of a page's footnote area continues the footnote left
        open at the bottom of the previous page: it is merged into that entry,
        which then spans both pages (``page``–``end_page``). When that footnote
        lies before ``start_page`` the continuation is kept as its own entry
        (``continued=True``) carrying the inherited number.
        """
        page_footnotes: Dict[int, List[Footnote]] = {}
        all_footnotes: List[Footnote] = []
        prev_open_num = cls.last_footnote_num(doc, start_page - 1, config) if start_page > 1 else None

        for pno in range(start_page - 1, end_page):
            page_num = pno + 1
            page_footnotes[page_num] = []
            entries = cls.page_entries(doc, page_num, config)
            if not entries:
                prev_open_num = None
                continue

            verse_parts = cls.split_verse_parts(entries, entries[0]['verse_lines'])
            for entry, parts in zip(entries, verse_parts):
                continued = entry['continued'] and prev_open_num is not None
                num = prev_open_num if continued else entry['orig_num']
                last = all_footnotes[-1] if all_footnotes else None
                if (continued and last is not None and last.orig_num == num
                        and last.end_page == page_num - 1):
                    cls.merge_continuation(last, entry['text'], parts, page_num)
                    continue
                fn_item = Footnote(
                    id=num,
                    orig_num=num,
                    page=page_num,
                    text=entry['text'],
                    parts=parts,
                    continued=continued,
                )
                page_footnotes[page_num].append(fn_item)
                all_footnotes.append(fn_item)
            prev_open_num = all_footnotes[-1].orig_num

        return page_footnotes, all_footnotes

    @staticmethod
    def merge_continuation(fn: Footnote, text: str, parts: List[Paragraph], page_num: int) -> None:
        """Append a footnote's continuation from ``page_num`` onto ``fn`` in place.

        The entry then spans ``fn.page``–``page_num``; prose joins with a space and
        verse split by the page break is rejoined into one ``Verse`` block.
        """
        if fn.parts or parts:
            merged: List[Paragraph] = list(fn.parts or [fn.text])
            for part in parts or [text]:
                if merged and isinstance(part, Verse) and isinstance(merged[-1], Verse):
                    merged[-1] = Verse(merged[-1].lines + part.lines)
                elif merged and isinstance(part, str) and isinstance(merged[-1], str):
                    merged[-1] = f"{merged[-1]} {part}".strip()
                else:
                    merged.append(part)
            fn.parts = merged
        fn.text = f"{fn.text} {text}".strip()
        fn.end_page = page_num
