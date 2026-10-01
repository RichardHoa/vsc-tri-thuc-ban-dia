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
from .discovery import PartLayout, PartLayoutDiscovery, StoryDiscoveryEngine
from .engine import StoryExtractionEngine
from .formatters import MarkdownRenderer, TableOfContentsBuilder
from .toc import PartRange, SectionRange, TableOfContentsParser, TocEntry
from .pipeline import BookPipeline, FolkStoryPipeline
from .verse import VerseDetector
from .survey import EdgeCaseSurvey, FootnoteChain
from .validation import (
    KNOWN_SOURCE_ERRATA,
    KNOWN_TOC_ERRATA,
    ExtractionValidator,
    LeafJob,
    apply_source_errata,
    check_completeness,
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
    "PartLayout",
    "PartLayoutDiscovery",
    "StoryExtractionEngine",
    "MarkdownRenderer",
    "TableOfContentsBuilder",
    "TocEntry",
    "SectionRange",
    "PartRange",
    "TableOfContentsParser",
    "FolkStoryPipeline",
    "BookPipeline",
    "StoryValidationResult",
    "ExtractionValidator",
    "KNOWN_SOURCE_ERRATA",
    "KNOWN_TOC_ERRATA",
    "LeafJob",
    "apply_source_errata",
    "check_completeness",
    "ValidationReporter",
    "normalize_for_diff",
    "strip_markdown_scaffolding",
    "extract_raw_page_text",
    "score_alignment",
]
