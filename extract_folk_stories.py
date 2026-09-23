#!/usr/bin/env python3
"""
Folk Story & Footnote Extractor for Vietnamese Folk Tales (data.pdf)
--------------------------------------------------------------------
CLI entrypoint to discover, extract, and format stories, Roman sections,
Khảo dị sections, and footnotes into Markdown and Table of Contents JSON.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

import fitz  # PyMuPDF

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
    TableOfContentsParser,
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
    parser.add_argument(
        "--section", default=None,
        help="Extract Roman section(s) from PHẦN THỨ HAI by 1-based index, e.g. 1, 1-3 or 1,4. "
             "Page ranges are read from the MỤC LỤC and override --start-page/--end-page. "
             "Each section is written to <output-dir>/<ROMAN>_<SECTION_NAME>/"
    )
    parser.add_argument("--list-sections", action="store_true", help="Print sections found in MỤC LỤC and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    return parser


def main():
    """Main CLI execution."""
    parser = build_cli_parser()
    args = parser.parse_args()

    try:
        if args.section is None and not args.list_sections:
            config = ExtractorConfig(
                pdf_path=args.pdf,
                start_page=args.start_page,
                end_page=args.end_page,
                output_dir=args.output_dir,
                story_number=args.story,
                verbose=args.verbose
            )
            FolkStoryPipeline(config).run()
            return

        with fitz.open(args.pdf) as doc:
            sections = TableOfContentsParser.parse_sections(doc)

        if args.list_sections:
            for s in sections:
                print(f"{s.index:>2}. {s.full_title}  (pages {s.start_page}-{s.end_page})")
            return

        for section in TableOfContentsParser.select_sections(sections, args.section):
            print(f"== Section {section.index}: {section.full_title} "
                  f"(pages {section.start_page}-{section.end_page})")
            config = ExtractorConfig(
                pdf_path=args.pdf,
                start_page=section.start_page,
                end_page=section.end_page,
                output_dir=os.path.join(args.output_dir, section.folder_name),
                story_number=args.story,
                hard_stops=section.hard_stops + [section.end_page + 1],
                verbose=args.verbose
            )
            FolkStoryPipeline(config).run()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
