"""
Domain Data Models for Vietnamese Folk Story Extractor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass
class Verse:
    """A run of verse lines (a poem or song) kept line-by-line, in reading order."""
    lines: List[str] = field(default_factory=list)


#: A story paragraph is either plain prose or a verse block.
Paragraph = Union[str, Verse]


@dataclass
class Footnote:
    """Represents a footnote item with local story id, source page, and text.

    ``text`` is always the flat prose of the entry (verse lines joined with
    spaces). ``parts`` is only populated when the entry contains verse: it then
    holds the same content split into prose strings and ``Verse`` blocks.
    A footnote continued over a page break is one entry spanning
    ``page``–``end_page``. ``continued`` marks a continuation kept on its own
    because the note it continues lies before the story's page range.
    """
    id: int
    orig_num: int
    page: int
    text: str
    parts: List[Paragraph] = field(default_factory=list)
    continued: bool = False
    #: Last page of an entry merged across a page break (``page`` when single-page).
    end_page: Optional[int] = None

    def __post_init__(self):
        if self.end_page is None:
            self.end_page = self.page


@dataclass
class StoryDefinition:
    """Metadata defining a leaf boundary discovered in the PDF.

    Used for every leaf kind: a Story, an Essay (``category`` = its Section) or
    an Introduction (``story_number`` 0, no ``title``, ``category`` = its Part).
    Stories start at the top of a page and own whole pages; Essays and
    Introductions start and end mid-page, so they carry ``body_top`` (body lines
    on ``start_page`` above it are skipped) and ``body_bottom`` (body lines on
    ``end_page`` at or below it are skipped).

    ``title`` and ``category`` are clean (no footnote markers): they go into the
    manifests. ``heading_title`` / ``category_heading`` are set only when the
    printed heading carries a footnote marker, and hold it with ``[^N]`` at its
    printed position, for rendering.
    """
    story_number: int
    title: str
    category: str
    start_page: int
    end_page: int
    start_y0: float
    body_top: Optional[float] = None
    body_bottom: Optional[float] = None
    heading_title: Optional[str] = None
    category_heading: Optional[str] = None


@dataclass
class StoryContent:
    """Full extracted content of a story."""
    category: str
    story_number: int
    title: str
    start_page: int
    end_page: int
    paragraphs: List[Paragraph] = field(default_factory=list)
    khao_di: List[Paragraph] = field(default_factory=list)
    footnotes: List[Footnote] = field(default_factory=list)
    #: Rendered headings with footnote markers (see ``StoryDefinition``).
    heading_title: Optional[str] = None
    category_heading: Optional[str] = None


@dataclass
class ExtractorConfig:
    """Extractor configuration thresholds and parameters."""
    pdf_path: str = "data.pdf"
    start_page: int = 86
    end_page: int = 200
    output_dir: str = "extracted_stories"
    story_number: Optional[int] = None
    # Pages where non-story material begins; stories are clamped to end before them
    hard_stops: List[int] = field(default_factory=list)
    min_header_y: float = 60.0
    max_footer_y: float = 745.0
    footer_fallback_y: float = 680.0
    superscript_max_font_size: float = 10.0
    # Verse detection (see extractor/verse.py): a line is verse when mostly
    # italic and either indented past verse_min_x0 (body/footnote text starts
    # at x0 ~88, paragraph indent ~99) or part of a run of short italic lines.
    verse_min_x0: float = 130.0
    verse_min_italic_ratio: float = 0.8
    verse_margin_max_x1: float = 420.0
    verse_margin_min_run: int = 2
    verbose: bool = False
