"""
Domain Data Models for Vietnamese Folk Story Extractor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Footnote:
    """Represents a footnote item with local story id, source page, and text."""
    id: int
    orig_num: int
    page: int
    text: str


@dataclass
class StoryDefinition:
    """Metadata defining a story boundary discovered in the PDF."""
    story_number: int
    title: str
    category: str
    start_page: int
    end_page: int
    start_y0: float


@dataclass
class StoryContent:
    """Full extracted content of a story."""
    category: str
    story_number: int
    title: str
    start_page: int
    end_page: int
    paragraphs: List[str] = field(default_factory=list)
    khao_di: List[str] = field(default_factory=list)
    footnotes: List[Footnote] = field(default_factory=list)


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
    verbose: bool = False
