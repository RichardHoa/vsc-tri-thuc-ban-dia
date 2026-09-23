"""
Story & Roman Category Discovery Engine.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
import fitz  # PyMuPDF

from .models import StoryDefinition
from .normalizer import TextNormalizer


class StoryDiscoveryEngine:
    """Discovers Roman numeral category headers and story boundaries across the PDF."""

    ROMAN_HEADER_PAT = re.compile(r'^([IVXLCDM]+)\s*[\.\-]?\s*(.+)$')
    STORY_TITLE_PAT = re.compile(r'^(\d+)\.\s+(.+)$')

    @classmethod
    def clean_category_title(cls, raw_title: str) -> Optional[Tuple[str, str]]:
        """Parses and validates a Roman category header, stripping trailing footnotes."""
        match = cls.ROMAN_HEADER_PAT.match(raw_title.strip())
        if not match:
            return None

        roman_num = match.group(1)
        title_text = match.group(2).strip()
        # Remove trailing footnote digits or section separators (e.g. '1', '- TRUYỆN VUI...')
        title_text = re.sub(r'^\-\s*', '', title_text).strip()
        title_clean = re.sub(r'\d+\s*$', '', title_text).strip()

        if TextNormalizer.is_all_caps(title_clean):
            full_header = f"{roman_num}. {title_clean}"
            return roman_num, full_header
        return None

    @classmethod
    def clean_story_title(cls, raw_title: str) -> Optional[Tuple[int, str]]:
        """Parses and cleans a story title, stripping footnote artifacts."""
        match = cls.STORY_TITLE_PAT.match(raw_title.strip())
        if not match:
            return None

        story_num = int(match.group(1))
        title_text = match.group(2).strip()

        # Strip trailing footnote digits (e.g. 'SỰ TÍCH CÁ HE1' -> 'SỰ TÍCH CÁ HE')
        title_clean = re.sub(r'\d+\s*$', '', title_text).strip()
        # Strip inline footnote digits before spaces (e.g. 'THÁC ĐAO1 HAY' -> 'THÁC ĐAO HAY')
        title_clean = re.sub(r'([A-ZÀ-Ỵ])\d+(\s+)', r'\1\2', title_clean)

        if TextNormalizer.is_all_caps(title_clean):
            return story_num, title_clean
        return None

    @classmethod
    def find_active_category_before(cls, doc: fitz.Document, start_page: int) -> str:
        """
        Scans backward from start_page to identify the active Roman category header,
        preventing incorrect fallback defaults when extracting arbitrary page ranges.
        """
        for pno in range(start_page - 1, -1, -1):
            page = doc[pno]
            blocks = page.get_text('dict').get('blocks', [])
            for b in blocks:
                if b.get('type') != 0:
                    continue
                if b['bbox'][1] > 250 or b['bbox'][1] < 40:
                    continue
                block_text = TextNormalizer.clean_spaces(
                    ' '.join(''.join(s['text'] for s in l['spans']).strip() for l in b['lines'])
                )
                category_info = cls.clean_category_title(block_text)
                if category_info:
                    return category_info[1]

        return "I. NGUỒN GỐC SỰ VẬT"

    @classmethod
    def discover_stories(
        cls,
        doc: fitz.Document,
        start_page: int,
        end_page: int
    ) -> List[StoryDefinition]:
        """
        Scans pages to discover Roman category headers and story titles,
        calculating precise boundary page ranges for each story.
        """
        current_category = cls.find_active_category_before(doc, start_page)
        story_definitions: List[StoryDefinition] = []

        # Scan extra pages beyond end_page to accurately detect the end boundary of the last story
        max_scan_page = min(len(doc), end_page + 10)

        for pno in range(start_page - 1, max_scan_page):
            page_num = pno + 1
            page = doc[pno]
            blocks = page.get_text('dict').get('blocks', [])
            blocks.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))

            for b in blocks:
                if b.get('type') != 0:
                    continue

                y0 = b['bbox'][1]
                if y0 > 250 or y0 < 40:
                    continue

                block_text = TextNormalizer.clean_spaces(
                    ' '.join(''.join(s['text'] for s in l['spans']).strip() for l in b['lines'])
                )

                category_info = cls.clean_category_title(block_text)
                if category_info:
                    current_category = category_info[1]
                    continue

                story_info = cls.clean_story_title(block_text)
                if story_info:
                    snum, stitle = story_info
                    story_definitions.append(StoryDefinition(
                        story_number=snum,
                        title=stitle,
                        category=current_category,
                        start_page=page_num,
                        end_page=page_num,
                        start_y0=y0
                    ))

        # Filter stories that start within the requested range
        selected_stories = [s for s in story_definitions if s.start_page <= end_page]

        # Calculate exact end page for each story
        for s in selected_stories:
            idx_in_all = story_definitions.index(s)
            if idx_in_all + 1 < len(story_definitions):
                next_s = story_definitions[idx_in_all + 1]
                # Story ends either on previous page or current page (never less than start_page)
                s.end_page = max(s.start_page, next_s.start_page - 1)
            else:
                s.end_page = min(len(doc), s.start_page + 4)

        return selected_stories
