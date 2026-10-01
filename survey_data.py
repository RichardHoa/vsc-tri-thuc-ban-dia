#!/usr/bin/env python3
"""
Edge-Case Survey CLI
--------------------
Scans data.pdf for the layout edge cases the extractor must handle — verse
(poem) runs, footnotes continued over a page break, recurring footnote numbers,
and dialogue dashes left open at a block/page end — and writes a Markdown
catalog listing every page where each pattern occurs.

Read-only against data.pdf. Non-zero exit only on an unhandled exception.
"""

from __future__ import annotations

import argparse
import os
import sys

import fitz  # PyMuPDF

from extractor import EdgeCaseSurvey, ExtractorConfig, TableOfContentsParser
from extractor.cli import add_selection_args, check_selection_args

DEFAULT_CATALOG = os.path.join(".scratch", "folk-story-pipeline-fixes", "edge-case-catalog.md")


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Survey data.pdf for poems, multi-page footnotes and dialogue page breaks",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--pdf", default="data.pdf", help="Path to data.pdf")
    add_selection_args(parser)
    parser.add_argument(
        "--pages", default=None,
        help="Survey an explicit 1-based page range A-B instead of --part/--section",
    )
    parser.add_argument("--catalog", default=DEFAULT_CATALOG, help="Markdown catalog output path")
    return parser


def main() -> None:
    parser = build_cli_parser()
    args = parser.parse_args()
    check_selection_args(parser, args)
    config = ExtractorConfig(pdf_path=args.pdf)
    try:
        with fitz.open(args.pdf) as doc:
            surveys = []
            if args.pages:
                lo, hi = (int(x) for x in args.pages.split("-", 1))
                print(f"== Surveying pages {lo}-{hi}")
                surveys.append(EdgeCaseSurvey.survey_range(doc, lo, hi, config, label=f"Pages {lo}-{hi}"))
            else:
                parts = TableOfContentsParser.parse_parts(doc)
                for part, sections in TableOfContentsParser.select_parts(parts, args.part, args.section):
                    for section in sections:
                        label = f"Part {part.number} · {section.index}. {section.full_title}"
                        print(f"== Surveying {label} (pages {section.start_page}-{section.end_page})")
                        surveys.append(EdgeCaseSurvey.survey_range(
                            doc, section.start_page, section.end_page, config,
                            label=label,
                            hard_stops=section.hard_stops,
                            with_stories=part.leaf_kind == "stories",
                        ))

        os.makedirs(os.path.dirname(os.path.abspath(args.catalog)), exist_ok=True)
        with open(args.catalog, "w", encoding="utf-8") as handle:
            handle.write(EdgeCaseSurvey.render_catalog(surveys))
        print(f"Catalog written: {args.catalog}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
