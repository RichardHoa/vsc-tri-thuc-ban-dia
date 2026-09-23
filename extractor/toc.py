"""
MỤC LỤC (Table of Contents) Parser.

Reads the printed table of contents at the front of data.pdf and resolves the
page range of every Roman-numeral story section in "PHẦN THỨ HAI"
(e.g. "I. NGUỒN GỐC SỰ VẬT" -> pages 86-203).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import fitz  # PyMuPDF

from .normalizer import TextNormalizer


@dataclass
class TocEntry:
    """A single MỤC LỤC line: its title and printed page number (== PDF page number)."""
    title: str
    page: int


@dataclass
class SectionRange:
    """A Roman-numeral story section and the PDF pages it covers."""
    index: int
    roman: str
    title: str
    start_page: int
    end_page: int
    # Pages inside the range where non-story material (volume front matter,
    # plates, reviews...) begins. Stories must end before these pages.
    hard_stops: List[int] = field(default_factory=list)

    @property
    def full_title(self) -> str:
        return f"{self.roman}. {self.title}"

    @property
    def folder_name(self) -> str:
        """Filesystem-safe folder name, e.g. 'I_NGUON_GOC_SU_VAT'."""
        ascii_title = unicodedata.normalize('NFKD', self.title.replace('Đ', 'D').replace('đ', 'd'))
        ascii_title = ascii_title.encode('ascii', 'ignore').decode('ascii')
        slug = re.sub(r'[^A-Za-z0-9]+', '_', ascii_title).strip('_').upper()
        return f"{self.roman}_{slug}"


class TableOfContentsParser:
    """Parses MỤC LỤC pages and derives story section page ranges."""

    TOC_MARKER = 'MỤC LỤC'
    ENTRY_END_PAT = re.compile(r'^(.*?)[\s…]*\.+\s*(\d+)\s*$')
    ROMAN_SECTION_PAT = re.compile(r'^([IVX]+)\s*[\.\-]+\s*(?:-\s*)?(.+)$')
    STORY_PAT = re.compile(r'^\[?\d+\]?\.\s+')
    PART_PAT = re.compile(r'^PHẦN\s+THỨ\s+(\S+)', re.IGNORECASE)
    KHAO_DI = 'KHẢO DỊ'

    @classmethod
    def find_toc_pages(cls, doc: fitz.Document, max_scan: int = 40) -> List[int]:
        """Returns 0-based indices of the consecutive MỤC LỤC pages."""
        start: Optional[int] = None
        for pno in range(min(max_scan, len(doc))):
            if cls.TOC_MARKER in doc[pno].get_text().upper():
                start = pno
                break
        if start is None:
            raise ValueError("Could not locate 'MỤC LỤC' in the PDF.")

        pages = [start]
        for pno in range(start + 1, len(doc)):
            text = doc[pno].get_text()
            if len(re.findall(r'\.{5,}\s*\d+', text)) < 3:
                break
            pages.append(pno)
        return pages

    @classmethod
    def parse_entries(cls, doc: fitz.Document) -> List[TocEntry]:
        """Parses all MỤC LỤC lines, joining titles that wrap across lines."""
        entries: List[TocEntry] = []
        pending: List[str] = []

        for pno in cls.find_toc_pages(doc):
            for raw_line in doc[pno].get_text().split('\n'):
                line = TextNormalizer.clean_spaces(TextNormalizer.normalize_encoding(raw_line))
                if not line or line.isdigit() or line.upper() == cls.TOC_MARKER:
                    continue
                pending.append(line)
                match = cls.ENTRY_END_PAT.match(' '.join(pending))
                if match:
                    title = TextNormalizer.clean_spaces(match.group(1)).rstrip('. ')
                    entries.append(TocEntry(title=title, page=int(match.group(2))))
                    pending = []
        return entries

    @classmethod
    def _parse_roman(cls, title: str) -> Optional[Tuple[str, str]]:
        match = cls.ROMAN_SECTION_PAT.match(title)
        if not match or not TextNormalizer.is_all_caps(match.group(2)):
            return None
        return match.group(1), match.group(2).strip()

    @classmethod
    def parse_sections(cls, doc: fitz.Document) -> List[SectionRange]:
        """Resolves page ranges of the Roman story sections in PHẦN THỨ HAI."""
        entries = cls.parse_entries(doc)

        # Restrict to PHẦN THỨ HAI (Phần thứ nhất / thứ ba reuse Roman numerals)
        part_two: List[TocEntry] = []
        in_part_two = False
        for entry in entries:
            part = cls.PART_PAT.match(entry.title)
            if part:
                in_part_two = part.group(1).upper() == 'HAI'
                if not in_part_two and part_two:
                    part_two.append(entry)  # sentinel marking the end of the last section
                    break
                continue
            if in_part_two:
                part_two.append(entry)

        sections: List[SectionRange] = []
        by_roman = {}
        current: Optional[SectionRange] = None
        last: Optional[SectionRange] = None

        for entry in part_two:
            roman_info = cls._parse_roman(entry.title)
            if roman_info:
                roman, title = roman_info
                if current is not None:
                    current.end_page = max(current.end_page, entry.page - 1)
                if roman in by_roman:
                    # Section continues in the next volume (e.g. III, IX)
                    current = by_roman[roman]
                else:
                    current = SectionRange(
                        index=len(sections) + 1, roman=roman, title=title,
                        start_page=entry.page, end_page=entry.page
                    )
                    sections.append(current)
                    by_roman[roman] = current
                last = current
                continue

            if cls.STORY_PAT.match(entry.title) or entry.title.upper() == cls.KHAO_DI:
                # Stories after a volume break without a repeated header continue the last section
                current = current or last
                if current is not None:
                    current.end_page = max(current.end_page, entry.page)
                continue

            if current is None:
                continue

            # Non-story material: closes the section until its Roman header reappears
            current.end_page = max(current.end_page, entry.page - 1)
            current.hard_stops.append(entry.page)
            current = None

        for section in sections:
            section.hard_stops = [p for p in section.hard_stops if p <= section.end_page]

        return sections

    @staticmethod
    def select_sections(sections: List[SectionRange], spec: str) -> List[SectionRange]:
        """Selects sections by a 1-based spec such as '1', '1-3' or '1,4-5'."""
        wanted: List[int] = []
        for part in spec.split(','):
            part = part.strip()
            match = re.fullmatch(r'(\d+)(?:\s*-\s*(\d+))?', part)
            if not match:
                raise ValueError(f"Invalid --section value '{part}' (expected e.g. 1 or 1-3).")
            lo = int(match.group(1))
            hi = int(match.group(2) or lo)
            if lo > hi:
                lo, hi = hi, lo
            wanted.extend(range(lo, hi + 1))

        valid = {s.index: s for s in sections}
        missing = [n for n in wanted if n not in valid]
        if missing:
            raise ValueError(
                f"Section(s) {missing} not found. Available: 1-{len(sections)}."
            )
        return [valid[n] for n in dict.fromkeys(wanted)]
