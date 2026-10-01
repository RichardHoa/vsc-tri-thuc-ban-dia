#!/usr/bin/env python3
"""
Folk Story & Footnote Extractor for Vietnamese Folk Tales (data.pdf)
--------------------------------------------------------------------
CLI entrypoint to discover, extract, and format the book's three Parts —
Stories (with Khảo dị), Essays, Introductions, Roman Sections and footnotes —
and the Bibliography (THƯ MỤC THAM KHẢO) into Markdown plus per-Section and
root Table of Contents JSON.
"""

from __future__ import annotations

import argparse
import sys

import fitz  # PyMuPDF

from extractor import BookPipeline, TableOfContentsParser
from extractor.cli import add_selection_args, check_selection_args


def build_cli_parser() -> argparse.ArgumentParser:
    """Builds and returns command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Extract the book's Parts, Sections, Stories, Essays and Introductions "
                    "from data.pdf into <output-dir>/<PART>/<ROMAN>_<SECTION_NAME>/",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--pdf", default="data.pdf", help="Path to data.pdf")
    parser.add_argument("--output-dir", default="extracted_stories", help="Output directory")
    add_selection_args(parser)
    parser.add_argument("--story", type=int, default=None,
                        help="Extract one Part 2 Story by number only (implies --part 2)")
    parser.add_argument("--bibliography", action="store_true",
                        help="Extract only the Bibliography (THƯ MỤC THAM KHẢO); a full run "
                             "includes it after the three Parts")
    parser.add_argument("--list-sections", action="store_true",
                        help="Print each Part's Sections found in MỤC LỤC and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    return parser


def main():
    """Main CLI execution."""
    parser = build_cli_parser()
    args = parser.parse_args()
    check_selection_args(parser, args)
    if args.bibliography and (args.part is not None or args.section is not None or args.story is not None):
        parser.error("--bibliography cannot be combined with --part, --section or --story.")

    try:
        if args.list_sections:
            with fitz.open(args.pdf) as doc:
                parts = TableOfContentsParser.parse_parts(doc)
            for part in parts:
                print(f"Part {part.number}: {part.full_title}  (pages {part.start_page}-{part.end_page})")
                for s in part.sections:
                    print(f"  {s.index:>2}. {s.full_title}  (pages {s.start_page}-{s.end_page})")
            return

        BookPipeline(
            pdf_path=args.pdf,
            output_dir=args.output_dir,
            part=args.part,
            section_spec=args.section,
            story_number=args.story,
            verbose=args.verbose,
            bibliography=args.bibliography,
        ).run()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
