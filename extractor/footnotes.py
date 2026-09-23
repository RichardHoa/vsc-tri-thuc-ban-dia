"""
Footnote Parsing, Re-indexing, and Extraction Engine.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple
import fitz  # PyMuPDF

from .models import ExtractorConfig, Footnote
from .normalizer import TextNormalizer
from .geometry import PdfGeometryHelper


class FootnoteEngine:
    """Parses, re-indexes, and formats footnotes."""

    FOOTNOTE_SPLIT_PAT = re.compile(r'(?:^|\s+)(\d+)[\.\s]+(?=[A-ZÀ-Ỵ\"\'“‘\(\[\d])')

    @classmethod
    def parse_footnote_text(cls, text: str, page_num: int) -> List[Dict[str, any]]:
        """
        Splits footnote block text into individual footnote entries.
        Supports single and sequential multi-footnote blocks (e.g. 1. ... 2. ...).
        """
        text = TextNormalizer.clean_spaces(text)
        if not text:
            return []

        # Fix OCR scanning artifact like '11.' for '1.' at start
        text = re.sub(r'^11\.\s*', '1. ', text)

        valid_splits = []
        expected_num = 1

        for match in cls.FOOTNOTE_SPLIT_PAT.finditer(text):
            num_val = int(match.group(1))
            if num_val == expected_num:
                valid_splits.append((num_val, match.start(1), match.end()))
                expected_num += 1

        if not valid_splits:
            m0 = re.match(r'^(\d+)[\.\s]+', text)
            if m0:
                content = TextNormalizer.clean_spaces(text[m0.end():])
                return [{'orig_num': int(m0.group(1)), 'page': page_num, 'text': content}]
            return [{'orig_num': 1, 'page': page_num, 'text': TextNormalizer.clean_spaces(text)}]

        items = []
        for i, (num, _, start_content) in enumerate(valid_splits):
            end_content = valid_splits[i + 1][1] if i + 1 < len(valid_splits) else len(text)
            content = TextNormalizer.clean_spaces(text[start_content:end_content])
            content = re.sub(r'^[\.\-\s]+', '', content)
            items.append({
                'orig_num': num,
                'page': page_num,
                'text': content
            })

        return items

    @staticmethod
    def collect_story_footnotes(
        doc: fitz.Document,
        start_page: int,
        end_page: int,
        config: ExtractorConfig
    ) -> Tuple[Dict[int, List[Footnote]], List[Footnote]]:
        """
        Scans story pages to extract footnotes and preserves original page-level footnote IDs.
        """
        page_footnotes: Dict[int, List[Footnote]] = {}
        all_footnotes: List[Footnote] = []

        for pno in range(start_page - 1, end_page):
            page_num = pno + 1
            page = doc[pno]
            page_footnotes[page_num] = []

            h_sep_y = PdfGeometryHelper.find_footer_separator_y(page)
            blocks = page.get_text('dict').get('blocks', [])
            blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))

            fn_lines: List[str] = []
            for b in blocks:
                if b.get('type') != 0:
                    continue
                for l in b.get('lines', []):
                    y0 = l['bbox'][1]
                    raw_line = ''.join(s['text'] for s in l.get('spans', [])).strip()
                    if not raw_line:
                        continue
                    if PdfGeometryHelper.is_footer_line(
                        y0, raw_line, h_sep_y, config.max_footer_y, config.footer_fallback_y
                    ) and y0 <= config.max_footer_y:
                        fn_lines.append(raw_line)

            if not fn_lines:
                continue

            combined_fn_text = ' '.join(
                TextNormalizer.normalize_encoding(line)
                for line in fn_lines
            )
            parsed_entries = FootnoteEngine.parse_footnote_text(combined_fn_text, page_num)
            if not parsed_entries and combined_fn_text.strip():
                parsed_entries = [{'orig_num': 1, 'page': page_num, 'text': TextNormalizer.clean_spaces(combined_fn_text)}]

            for entry in parsed_entries:
                fn_item = Footnote(
                    id=entry['orig_num'],
                    orig_num=entry['orig_num'],
                    page=page_num,
                    text=entry['text']
                )
                page_footnotes[page_num].append(fn_item)
                all_footnotes.append(fn_item)

        return page_footnotes, all_footnotes
