"""
Folk Story Extractor Package.
"""

from .models import (
    Footnote,
    StoryDefinition,
    StoryContent,
    ExtractorConfig,
)
from .normalizer import TextNormalizer
from .geometry import PdfGeometryHelper
from .footnotes import FootnoteEngine
from .discovery import StoryDiscoveryEngine
from .engine import StoryExtractionEngine
from .formatters import MarkdownRenderer, TableOfContentsBuilder
from .toc import SectionRange, TableOfContentsParser, TocEntry
from .pipeline import FolkStoryPipeline
from .validation import (
    ExtractionValidator,
    StoryValidationResult,
    ValidationReporter,
    extract_raw_page_text,
    normalize_for_diff,
    score_alignment,
    strip_markdown_scaffolding,
)

__all__ = [
    "Footnote",
    "StoryDefinition",
    "StoryContent",
    "ExtractorConfig",
    "TextNormalizer",
    "PdfGeometryHelper",
    "FootnoteEngine",
    "StoryDiscoveryEngine",
    "StoryExtractionEngine",
    "MarkdownRenderer",
    "TableOfContentsBuilder",
    "TocEntry",
    "SectionRange",
    "TableOfContentsParser",
    "FolkStoryPipeline",
    "StoryValidationResult",
    "ExtractionValidator",
    "ValidationReporter",
    "normalize_for_diff",
    "strip_markdown_scaffolding",
    "extract_raw_page_text",
    "score_alignment",
]
