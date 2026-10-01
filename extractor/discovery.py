"""
Story & Roman Category Discovery Engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import fitz  # PyMuPDF

from .models import ExtractorConfig, StoryDefinition
from .normalizer import TextNormalizer
from .geometry import PdfGeometryHelper
from .toc import PartRange, TableOfContentsParser

_MARKER_PAT = re.compile(r'\s*(\[\^\d+\])')


def insert_heading_markers(title: str, marked: str) -> str:
    """``title`` with the footnote markers of the printed heading ``marked``.

    ``marked`` is the heading as printed, superscripts already turned into
    ``[^N]`` (and still carrying its ``13. `` / ``III. `` prefix). Each marker
    is placed after the same letter it follows in print, counted from the end
    of the heading, and attached to that word. When the two disagree on that
    tail of text, the clean ``title`` is returned unchanged.
    """
    markers: List[Tuple[int, str]] = []  # (non-space chars after the marker, marker)
    plain_parts: List[str] = []
    pos = 0
    for m in _MARKER_PAT.finditer(marked):
        plain_parts.append(marked[pos:m.start()])
        pos = m.end()
        markers.append((len(re.sub(r'\s', '', _MARKER_PAT.sub('', marked[pos:]))), m.group(1)))
    if not markers:
        return title
    plain_parts.append(marked[pos:])
    printed = re.sub(r'\s', '', ''.join(plain_parts))
    clean = re.sub(r'\s', '', title)

    # Indices of the title's non-space chars; a marker followed by ``after``
    # of them goes right after the char before those.
    letters = [i for i, c in enumerate(title) if not c.isspace()]
    inserts: List[Tuple[int, int, str]] = []
    for after, marker in markers:
        if after >= len(clean) or clean[len(clean) - after:] != printed[len(printed) - after:]:
            return title
        inserts.append((letters[len(letters) - after - 1] + 1, len(inserts), marker))
    out = title
    for idx, _, marker in sorted(inserts, reverse=True):
        out = out[:idx] + marker + out[idx:]
    return out


class StoryDiscoveryEngine:
    """Discovers Roman numeral category headers and story boundaries across the PDF."""

    ROMAN_HEADER_PAT = re.compile(r'^([IVXLCDM]+)\s*[\.\-]?\s*(.+)$')
    STORY_TITLE_PAT = re.compile(r'^\[?(\d+)\]?\.\s+(.+)$')

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

    @staticmethod
    def marked_heading(title: str, block: Dict, config: ExtractorConfig) -> Optional[str]:
        """``title`` with the footnote markers printed in its heading ``block``,
        or ``None`` when the heading carries none."""
        lines = []
        for l in block['lines']:
            text = ''
            for s in l['spans']:
                marker = (TextNormalizer.superscript_marker(s['text'])
                          if s['size'] < config.superscript_max_font_size else None)
                text += marker if marker is not None else s['text']
            lines.append(text.strip())
        marked = TextNormalizer.clean_spaces(' '.join(lines))
        if not _MARKER_PAT.search(marked):
            return None
        heading = insert_heading_markers(title, marked)
        return heading if heading != title else None

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
        end_page: int,
        config: Optional[ExtractorConfig] = None,
    ) -> List[StoryDefinition]:
        """
        Scans pages to discover Roman category headers and story titles,
        calculating precise boundary page ranges for each story.
        """
        config = config or ExtractorConfig()
        current_category = cls.find_active_category_before(doc, start_page)
        # (page, marked heading) of a Section heading carrying a footnote marker.
        category_heading: Optional[Tuple[int, str]] = None
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
                    marked = cls.marked_heading(category_info[1], b, config)
                    category_heading = (page_num, marked) if marked else None
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
                        start_y0=y0,
                        heading_title=cls.marked_heading(stitle, b, config),
                        # A Section heading's marker renders in the Story it opens.
                        category_heading=(category_heading[1] if category_heading
                                          and category_heading[0] == page_num else None),
                    ))
                    category_heading = None

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


@dataclass
class PartLayout:
    """A Part's Introduction and Essays, as printed (Story discovery is separate)."""
    introduction: Optional[StoryDefinition] = None
    #: Essays per Section Roman numeral, in reading order.
    essays: Dict[str, List[StoryDefinition]] = field(default_factory=dict)


@dataclass
class _Heading:
    kind: str  # 'title' | 'section' | 'essay'
    page: int
    top: float
    bottom: float
    roman: str = ""
    number: int = 0
    title: str = ""


class PartLayoutDiscovery:
    """Finds a Part's Introduction and its Essays from the printed headings.

    Essays start and end mid-page, so each leaf is bounded by heading
    positions: it runs from below its own heading to the top of the next
    heading (Essay, Section or end of Part). MỤC LỤC is only the guide — an
    Essay heading printed in the text but missing from MỤC LỤC (Part 3 V.1) is
    still found.
    """

    ESSAY_HEADING_PAT = re.compile(r'^\[?(\d+)\]?\s*\.\s*(.+)$')
    #: Share of upper-case letters for a line to count as an all-caps heading.
    #: Tolerates a stray lower-case letter printed inside a heading (p. 1356).
    CAPS_RATIO = 0.9

    @classmethod
    def is_mostly_caps(cls, text: str) -> bool:
        letters = [c for c in text if c.isalpha()]
        if len(letters) < 2:
            return False
        return sum(c.isupper() for c in letters) / len(letters) >= cls.CAPS_RATIO

    @classmethod
    def parse_essay_heading(cls, text: str) -> Optional[Tuple[int, str]]:
        """``(number, title)`` for an all-caps ``N. TITLE`` line, else ``None``.

        Mixed-case numbered lines are prose lists, not headings.
        """
        text = TextNormalizer.clean_spaces(text)
        if TableOfContentsParser._parse_roman(text):
            return None
        match = cls.ESSAY_HEADING_PAT.match(text)
        if not match:
            return None
        title = cls.clean_heading_text(match.group(2))
        if not cls.is_mostly_caps(title):
            return None
        return int(match.group(1)), title

    @staticmethod
    def clean_heading_text(text: str) -> str:
        """Strips footnote digits and the closing period from a heading's text."""
        text = re.sub(r'\d+\s*$', '', text.strip())
        text = re.sub(r'([A-ZÀ-Ỵ])\d+(\s+)', r'\1\2', text)
        return TextNormalizer.clean_spaces(text).rstrip('. ')

    @staticmethod
    def _body_lines(page: fitz.Page, config: ExtractorConfig) -> List[Tuple[float, float, str]]:
        """``(y0, y1, text)`` of a page's non-empty body lines, top to bottom."""
        h_sep_y = PdfGeometryHelper.find_footer_separator_y(page)
        out = []
        for b in page.get_text('dict').get('blocks', []):
            if b.get('type') != 0:
                continue
            for l in b.get('lines', []):
                raw = ''.join(s['text'] for s in l.get('spans', []))
                text = TextNormalizer.clean_spaces(TextNormalizer.normalize_encoding(raw))
                y0, y1 = l['bbox'][1], l['bbox'][3]
                if not text or PdfGeometryHelper.is_header_line(y0, config.min_header_y):
                    continue
                if PdfGeometryHelper.is_footer_line(
                        y0, raw, h_sep_y, config.max_footer_y, config.footer_fallback_y):
                    continue
                out.append((y0, y1, text))
        out.sort(key=lambda t: t[0])
        return out

    @classmethod
    def _scan_headings(
        cls, doc: fitz.Document, part: PartRange, config: ExtractorConfig
    ) -> Tuple[List[_Heading], Dict[int, List[Tuple[float, float, str]]]]:
        """Part title, Section and Essay headings in reading order, plus each page's body lines."""
        romans = {s.roman for s in part.sections}
        want_essays = part.leaf_kind == "essays"
        headings: List[_Heading] = []
        page_lines: Dict[int, List[Tuple[float, float, str]]] = {}

        for page_num in range(part.start_page, part.end_page + 1):
            lines = cls._body_lines(doc[page_num - 1], config)
            page_lines[page_num] = lines
            i = 0
            if page_num == part.start_page:
                # The Part heading and its title, e.g. "PHẦN THỨ BA" / "NHẬN ĐỊNH ... VIỆT-" / "NAM".
                while i < len(lines) and (TableOfContentsParser.PART_PAT.match(lines[i][2])
                                          or cls.is_mostly_caps(lines[i][2])):
                    i += 1
                if i:
                    headings.append(_Heading('title', page_num, lines[0][0], lines[i - 1][1]))
            while i < len(lines):
                y0, y1, text = lines[i]
                i += 1
                roman_info = TableOfContentsParser._parse_roman(text)
                if roman_info and roman_info[0] in romans:
                    headings.append(_Heading('section', page_num, y0, y1, roman=roman_info[0]))
                    if not want_essays:
                        return headings, page_lines
                    continue
                essay = cls.parse_essay_heading(text) if want_essays else None
                if essay is None:
                    continue
                parts = [essay[1]]
                bottom = y1
                # A long heading wraps over several lines (and blocks).
                while (i < len(lines) and cls.is_mostly_caps(lines[i][2])
                       and not cls.ESSAY_HEADING_PAT.match(lines[i][2])
                       and not TableOfContentsParser._parse_roman(lines[i][2])):
                    parts.append(cls.clean_heading_text(lines[i][2]))
                    bottom = lines[i][1]
                    i += 1
                title = TextNormalizer.clean_spaces(' '.join(parts)).rstrip('. ')
                headings.append(_Heading('essay', page_num, y0, bottom, number=essay[0], title=title))
        return headings, page_lines

    @classmethod
    def discover(cls, doc: fitz.Document, part: PartRange, config: ExtractorConfig) -> PartLayout:
        """Bounds of the Part's Introduction and (Parts 1, 3) its Essays."""
        headings, page_lines = cls._scan_headings(doc, part, config)
        layout = PartLayout()

        def bounded(start: _Heading, nxt: Optional[_Heading], **fields) -> Optional[StoryDefinition]:
            """The leaf below ``start`` up to ``nxt``; ``None`` when it holds no body text."""
            if nxt is None:
                end_page, body_bottom = part.end_page, None
            elif any(y0 < nxt.top for y0, _, _ in page_lines.get(nxt.page, [])):
                end_page, body_bottom = nxt.page, nxt.top
            else:
                end_page, body_bottom = nxt.page - 1, None
            has_text = any(
                not (p == start.page and y0 < start.bottom)
                and not (p == end_page and body_bottom is not None and y0 >= body_bottom)
                for p in range(start.page, end_page + 1)
                for y0, _, _ in page_lines.get(p, [])
            )
            if not has_text:
                return None
            return StoryDefinition(
                start_page=start.page, end_page=end_page, start_y0=start.top,
                body_top=start.bottom, body_bottom=body_bottom, **fields,
            )

        sections = {s.roman: s for s in part.sections}
        current_section: Optional[str] = None
        for idx, heading in enumerate(headings):
            nxt = headings[idx + 1] if idx + 1 < len(headings) else None
            if heading.kind == 'title':
                layout.introduction = bounded(
                    heading, nxt, story_number=0, title="", category=part.full_title)
            elif heading.kind == 'section':
                current_section = heading.roman
                layout.essays.setdefault(heading.roman, [])
            elif current_section is not None:
                essay = bounded(heading, nxt, story_number=heading.number, title=heading.title,
                                category=sections[current_section].full_title)
                if essay is not None:
                    layout.essays[current_section].append(essay)
        if part.leaf_kind != "essays":
            layout.essays = {}
        return layout
