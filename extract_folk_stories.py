#!/usr/bin/env python3
"""
Folk Story & Footnote Extractor for Vietnamese Folk Tales (data.pdf)
--------------------------------------------------------------------
CLI entrypoint to discover, extract, and format stories, Roman sections,
Khảo dị sections, and footnotes into Markdown and Table of Contents JSON.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from extractor import (
    ExtractorConfig,
    FolkStoryPipeline,
    Footnote,
    FootnoteEngine,
    MarkdownRenderer,
    PdfGeometryHelper,
    StoryContent,
    StoryDefinition,
    StoryDiscoveryEngine,
    StoryExtractionEngine,
    TableOfContentsBuilder,
    TextNormalizer,
)


def build_cli_parser() -> argparse.ArgumentParser:
    """Builds and returns command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Extract Vietnamese Folk Tales and Table of Contents from data.pdf",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--pdf", default="data.pdf", help="Path to data.pdf")
    parser.add_argument("--start-page", type=int, default=86, help="Start page number (1-based)")
    parser.add_argument("--end-page", type=int, default=200, help="End page number (1-based)")
    parser.add_argument("--output-dir", default="extracted_stories", help="Output directory")
    parser.add_argument("--story", type=int, default=None, help="Extract specific story number only")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    return parser


def main():
    """Main CLI execution."""
    parser = build_cli_parser()
    args = parser.parse_args()

    config = ExtractorConfig(
        pdf_path=args.pdf,
        start_page=args.start_page,
        end_page=args.end_page,
        output_dir=args.output_dir,
        story_number=args.story,
        verbose=args.verbose
    )

    try:
        pipeline = FolkStoryPipeline(config)
        pipeline.run()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
