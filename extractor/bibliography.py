"""
Bibliography (THƯ MỤC THAM KHẢO) Extraction.

The Bibliography is the one extracted piece of back matter: opening prose and
an abbreviation key, then Roman Sections of Bibliography entries. Its page
range comes from MỤC LỤC (its heading → the next entry that is not one of its
Sections); its Sections come from the printed headings, because Section III
(TÀI LIỆU CHÉP TAY) is printed but missing from MỤC LỤC.

Entries are typeset with a hanging indent: an entry's first line starts at the
paragraph indent, its wrapped lines start further left. A work printed as
``- <title>`` belongs to the author of the entry above it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

from .normalizer import TextNormalizer
from .toc import TableOfContentsParser, ascii_slug

#: Lines starting at least this far right open a new entry / paragraph
#: (first lines sit at x≈99, wrapped lines at x≈88).
ENTRY_INDENT_X = 94.0


@dataclass
class BibliographyBlock:
    """One entry (or intro paragraph) with its wrapped lines joined."""
    text: str
    page: int


@dataclass
class BibliographySection:
    roman: str
    title: str
    start_page: int
    end_page: int = 0
    entries: List[BibliographyBlock] = field(default_factory=list)

    @property
    def full_title(self) -> str:
        return f"{self.roman}. {self.title}"

    @property
    def file_name(self) -> str:
        """'I_SACH_VA_BAI.md'."""
        return f"{self.roman}_{ascii_slug(self.title)}.md"


@dataclass
class Bibliography:
    title: str
    start_page: int
    end_page: int
    introduction: List[BibliographyBlock] = field(default_factory=list)
    sections: List[BibliographySection] = field(default_factory=list)

    @property
    def folder_name(self) -> str:
        """'THU_MUC_THAM_KHAO'."""
        return ascii_slug(self.title)


class BibliographyParser:
    """Reads the Bibliography's pages into introduction blocks and Sections."""

    HEADING = 'THƯ MỤC THAM KHẢO'
    #: Section headings are accepted only in sequence, so a wrapped line such
    #: as "VI, VII, 1885 - 86." is never mistaken for one.
    ROMANS = ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X')

    @classmethod
    def page_range(cls, doc: fitz.Document) -> tuple:
        """``(start, end)``: the MỤC LỤC heading's page to the page before the
        first following entry that is not a Roman Section."""
        entries = TableOfContentsParser.parse_entries(doc)
        for i, entry in enumerate(entries):
            if entry.title.upper() != cls.HEADING:
                continue
            following = (e for e in entries[i + 1:] if not TableOfContentsParser._parse_roman(e.title))
            nxt = next(following, None)
            return entry.page, (nxt.page - 1 if nxt else len(doc))
        raise ValueError(f"Could not locate '{cls.HEADING}' in MỤC LỤC.")

    @classmethod
    def parse(cls, doc: fitz.Document) -> Bibliography:
        start, end = cls.page_range(doc)
        bib = Bibliography(title=cls.HEADING, start_page=start, end_page=end)
        blocks = bib.introduction
        current: Optional[BibliographySection] = None

        for page in range(start, end + 1):
            for x, text in cls._page_lines(doc, page):
                if text.isdigit():
                    continue  # running page number
                if page == start and text.upper() == cls.HEADING:
                    continue
                roman = TableOfContentsParser._parse_roman(text) if x >= ENTRY_INDENT_X else None
                if roman and roman[0] == cls.ROMANS[min(len(bib.sections), len(cls.ROMANS) - 1)]:
                    current = BibliographySection(roman=roman[0], title=roman[1], start_page=page)
                    bib.sections.append(current)
                    blocks = current.entries
                    continue
                if blocks and (x < ENTRY_INDENT_X or cls._closes_open_paren(blocks[-1].text, text)):
                    blocks[-1].text = TextNormalizer.clean_spaces(f"{blocks[-1].text} {text}")
                else:
                    blocks.append(BibliographyBlock(text=TextNormalizer.clean_spaces(text), page=page))
                if current is not None:
                    current.end_page = page
        return bib

    @staticmethod
    def _closes_open_paren(block: str, line: str) -> bool:
        """A wrapped line printed without the hanging indent ("Thị Tịnh)" on
        page 1466): it closes a parenthesis the block left open. A bare open
        parenthesis is not enough — some printed entries never close theirs."""
        return block.count('(') > block.count(')') and line.count(')') > line.count('(')

    @staticmethod
    def _page_lines(doc: fitz.Document, page: int):
        """``(x0, text)`` for every non-empty text line of a 1-based page."""
        for block in doc[page - 1].get_text('dict')['blocks']:
            for line in block.get('lines', []):
                text = TextNormalizer.clean_spaces(''.join(s['text'] for s in line['spans']))
                if text:
                    yield line['bbox'][0], text


class BibliographyRenderer:
    """Markdown for the Bibliography's introduction and Sections."""

    @staticmethod
    def render_introduction(bib: Bibliography) -> str:
        """Prose paragraphs; the lines after a paragraph ending in ':' (the
        abbreviation key) as a list."""
        lines = [f"# {bib.title}\n"]
        in_list = False
        for block in bib.introduction:
            if in_list:
                lines.append(f"- {block.text}")
            else:
                lines.append(f"{block.text}\n")
                in_list = block.text.endswith(':')
        return "\n".join(lines) + "\n"

    @staticmethod
    def render_section(bib: Bibliography, section: BibliographySection) -> str:
        """One list item per entry; a ``- `` work nests under the entry above."""
        lines = [f"# {bib.title}\n", f"## {section.full_title}\n"]
        for entry in section.entries:
            if entry.text.startswith('- ') and len(lines) > 2:
                lines.append(f"  - {entry.text[2:]}")
            else:
                lines.append(f"- {entry.text}")
        return "\n".join(lines) + "\n"


class BibliographyWriter:
    """Writes ``<output_dir>/THU_MUC_THAM_KHAO/`` and returns its manifest."""

    INTRODUCTION_FILE = "introduction.md"
    MANIFEST_FILE = "table_of_contents.json"

    @classmethod
    def write(cls, doc: fitz.Document, output_dir: str) -> Dict[str, Any]:
        bib = BibliographyParser.parse(doc)
        folder = os.path.join(output_dir, bib.folder_name)
        os.makedirs(folder, exist_ok=True)
        print(f"== {bib.title} (pages {bib.start_page}-{bib.end_page})")

        with open(os.path.join(folder, cls.INTRODUCTION_FILE), 'w', encoding='utf-8') as f:
            f.write(BibliographyRenderer.render_introduction(bib))
        sections = []
        for section in bib.sections:
            print(f"== Section {section.full_title} (pages {section.start_page}-{section.end_page}, "
                  f"{len(section.entries)} entries)")
            with open(os.path.join(folder, section.file_name), 'w', encoding='utf-8') as f:
                f.write(BibliographyRenderer.render_section(bib, section))
            sections.append({
                'section_id': section.roman,
                'section_title': section.full_title,
                'markdown_file': f"{bib.folder_name}/{section.file_name}",
                'start_page': section.start_page,
                'end_page': section.end_page,
                'entry_count': len(section.entries),
            })
        return {
            'title': bib.title,
            'folder': bib.folder_name,
            'start_page': bib.start_page,
            'end_page': bib.end_page,
            'introduction': f"{bib.folder_name}/{cls.INTRODUCTION_FILE}",
            'sections': sections,
        }
