"""
MỤC LỤC (Table of Contents) Parser.

Reads the printed table of contents at the front of data.pdf and resolves the
book's Part → Section hierarchy: each Part's page range (Part heading → next
Part heading / LỜI SAU SÁCH) and the page range of every Roman-numeral Section
inside it (e.g. Part 2 "I. NGUỒN GỐC SỰ VẬT" -> pages 86-203).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import fitz  # PyMuPDF

from .normalizer import TextNormalizer


@dataclass
class TocEntry:
    """A single MỤC LỤC line: its title and printed page number (== PDF page number)."""
    title: str
    page: int


def ascii_slug(text: str) -> str:
    """Upper-case ASCII slug for folder names ('NGUỒN GỐC SỰ VẬT' -> 'NGUON_GOC_SU_VAT')."""
    ascii_text = unicodedata.normalize('NFKD', text.replace('Đ', 'D').replace('đ', 'd'))
    ascii_text = ascii_text.encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^A-Za-z0-9]+', '_', ascii_text).strip('_').upper()


@dataclass
class SectionRange:
    """A Roman-numeral Section of a Part and the PDF pages it covers."""
    index: int
    roman: str
    title: str
    start_page: int
    end_page: int
    # Pages inside the range where non-leaf material (volume front matter,
    # plates, reviews...) begins. Stories must end before these pages.
    hard_stops: List[int] = field(default_factory=list)
    #: Folder of the owning Part ('PHAN_THU_HAI'); Roman numerals repeat across Parts.
    part_folder: str = ""

    @property
    def full_title(self) -> str:
        return f"{self.roman}. {self.title}"

    @property
    def folder_name(self) -> str:
        """Filesystem-safe folder name, e.g. 'I_NGUON_GOC_SU_VAT'."""
        return f"{self.roman}_{ascii_slug(self.title)}"

    @property
    def path(self) -> str:
        """Output path relative to the extraction root, e.g. 'PHAN_THU_HAI/I_NGUON_GOC_SU_VAT'."""
        return f"{self.part_folder}/{self.folder_name}" if self.part_folder else self.folder_name


@dataclass
class PartRange:
    """One of the book's three Parts: its PDF pages and its Sections."""
    number: int
    #: Ordinal word of the printed heading ('NHẤT', 'HAI', 'BA').
    ordinal: str
    title: str
    start_page: int
    end_page: int
    sections: List[SectionRange] = field(default_factory=list)

    @property
    def heading(self) -> str:
        return f"PHẦN THỨ {self.ordinal}"

    @property
    def full_title(self) -> str:
        return f"{self.heading}. {self.title}" if self.title else self.heading

    @property
    def folder_name(self) -> str:
        """'PHAN_THU_NHAT', 'PHAN_THU_HAI', 'PHAN_THU_BA'."""
        return ascii_slug(self.heading)

    @property
    def leaf_kind(self) -> str:
        """'stories' for the anthology (Part 2), 'essays' for the scholarly Parts."""
        return "stories" if self.number == 2 else "essays"


class TableOfContentsParser:
    """Parses MỤC LỤC pages and derives story section page ranges."""

    TOC_MARKER = 'MỤC LỤC'
    ENTRY_END_PAT = re.compile(r'^(.*?)[\s…]*\.+\s*(\d+)\s*$')
    ROMAN_SECTION_PAT = re.compile(r'^([IVX]+)\s*[\.\-]+\s*(?:-\s*)?(.+)$')
    # A numbered leaf entry (Story or Essay). Part 3 prints "3.TÍNH CÁCH ..." with no space.
    STORY_PAT = re.compile(r'^\[?\d+\]?\.\s*\S')
    PART_PAT = re.compile(r'^PHẦN\s+THỨ\s+(\S+)', re.IGNORECASE)
    PART_NUMBERS: Dict[str, int] = {'NHẤT': 1, 'HAI': 2, 'BA': 3}
    #: MỤC LỤC entry where the back matter (and so Part 3) begins.
    BACK_MATTER = 'LỜI SAU SÁCH'
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
    def parse_parts(cls, doc: fitz.Document) -> List[PartRange]:
        """Resolves the three Parts and their Sections from the MỤC LỤC.

        A Part runs from its heading to the page before the next Part's heading
        (or LỜI SAU SÁCH for Part 3). Part 2's heading is repeated at every Volume
        start; a repeat of the current Part's heading does not open a new Part.
        """
        parts: List[PartRange] = []
        part_entries: List[List[TocEntry]] = []
        entries = cls.parse_entries(doc)
        i = 0
        while i < len(entries):
            entry = entries[i]
            i += 1
            match = cls.PART_PAT.match(entry.title)
            ordinal = match.group(1).upper() if match else None
            if ordinal in cls.PART_NUMBERS and (not parts or parts[-1].ordinal != ordinal):
                if parts:
                    parts[-1].end_page = entry.page - 1
                title = ""
                if i < len(entries) and entries[i].page == entry.page:
                    title = entries[i].title  # the Part's own title line
                    i += 1
                parts.append(PartRange(
                    number=cls.PART_NUMBERS[ordinal], ordinal=ordinal, title=title,
                    start_page=entry.page, end_page=entry.page,
                ))
                part_entries.append([])
                continue
            if not parts:
                continue  # front matter
            if entry.title.upper() == cls.BACK_MATTER:
                parts[-1].end_page = entry.page - 1
                break
            if match:
                continue  # a Volume repeat of the current Part's heading
            part_entries[-1].append(entry)
            parts[-1].end_page = max(parts[-1].end_page, entry.page)

        for part, own in zip(parts, part_entries):
            # Sentinel: whatever follows the Part closes its last Section.
            part.sections = cls._sections_from_entries(own + [TocEntry('', part.end_page + 1)])
            for section in part.sections:
                section.part_folder = part.folder_name
        return parts

    @classmethod
    def _sections_from_entries(cls, entries: List[TocEntry]) -> List[SectionRange]:
        """Resolves the Roman Sections among one Part's MỤC LỤC entries."""
        sections: List[SectionRange] = []
        by_roman = {}
        current: Optional[SectionRange] = None
        last: Optional[SectionRange] = None

        for entry in entries:
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

            # Non-leaf material: closes the section until its Roman header reappears
            current.end_page = max(current.end_page, entry.page - 1)
            current.hard_stops.append(entry.page)
            current = None

        for section in sections:
            section.hard_stops = [p for p in section.hard_stops if p <= section.end_page]

        return sections

    @classmethod
    def select_parts(
        cls, parts: List[PartRange], part: Optional[int], section_spec: Optional[str]
    ) -> List[Tuple[PartRange, List[SectionRange]]]:
        """Applies the shared CLI selection rules.

        ``--part N`` selects a Part, ``--section SPEC`` selects Sections within it
        (1-based MỤC LỤC index within that Part). ``--section`` without ``--part``
        is an error; no selection means every Part.
        """
        if section_spec is not None and part is None:
            raise ValueError("--section requires --part (Section numbering restarts in every Part).")
        if part is None:
            return [(p, list(p.sections)) for p in parts]
        chosen = [p for p in parts if p.number == part]
        if not chosen:
            raise ValueError(f"--part {part} not found. Available: {[p.number for p in parts]}.")
        target = chosen[0]
        if section_spec is None:
            return [(target, list(target.sections))]
        return [(target, cls.select_sections(target.sections, section_spec))]

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
