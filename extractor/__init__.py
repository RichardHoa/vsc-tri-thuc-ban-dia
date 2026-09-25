"""
Folk Story Extractor Package.
"""

from .models import (
    Footnote,
    StoryDefinition,
    StoryContent,
    ExtractorConfig,
    Verse,
)
from .normalizer import TextNormalizer
from .geometry import PdfGeometryHelper
from .footnotes import FootnoteEngine
from .discovery import StoryDiscoveryEngine
from .engine import StoryExtractionEngine
from .formatters import MarkdownRenderer, TableOfContentsBuilder
from .toc import SectionRange, TableOfContentsParser, TocEntry
from .pipeline import FolkStoryPipeline
from .verse import VerseDetector
from .survey import EdgeCaseSurvey, FootnoteChain
from .validation import (
    KNOWN_SOURCE_ERRATA,
    ExtractionValidator,
    apply_source_errata,
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
    "Verse",
    "VerseDetector",
    "EdgeCaseSurvey",
    "FootnoteChain",
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
    "KNOWN_SOURCE_ERRATA",
    "apply_source_errata",
    "ValidationReporter",
    "normalize_for_diff",
    "strip_markdown_scaffolding",
    "extract_raw_page_text",
    "score_alignment",
]
