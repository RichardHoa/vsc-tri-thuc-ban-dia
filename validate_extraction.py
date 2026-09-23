#!/usr/bin/env python3
"""
Extraction Accuracy Validator CLI
---------------------------------
Validates already-extracted folk-story output (``story_NNN.md`` +
``table_of_contents.json``) against data.pdf: structural checks plus a
deterministic difflib text-alignment score, reported worst-first.

Read-only against extraction logic. Always exits 0 — this is a reporting tool,
not a CI gate. Gaps and failures are reported in the output, never raised.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

import fitz  # PyMuPDF

from extractor import (
    ExtractionValidator,
    ExtractorConfig,
    FolkStoryPipeline,
    SectionRange,
    TableOfContentsParser,
    ValidationReporter,
)


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate extracted folk-story Markdown against data.pdf",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--pdf", default="data.pdf", help="Path to data.pdf")
    parser.add_argument(
        "--section", default=None,
        help="1-based Roman section index from MỤC LỤC; resolves <output-dir>/<ROMAN>_<NAME>/",
    )
    parser.add_argument("--output-dir", default="extracted_stories", help="Extraction output root")
    parser.add_argument(
        "--input-dir", default=None,
        help="Explicit directory holding table_of_contents.json (overrides --section resolution)",
    )
    parser.add_argument("--threshold", type=float, default=0.90,
                        help="rendered_coverage below this marks a story REVIEW")
    parser.add_argument("--report", default=None,
                        help="Markdown report path (default: <input-dir>/validation_report.md)")
    parser.add_argument("--extract-first", action="store_true",
                        help="Run extraction for the section before validating (opt-in)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return parser


def _resolve_section(pdf_path: str, spec: str) -> Optional[SectionRange]:
    """Resolve a 1-based section spec to its SectionRange; None on any failure."""
    try:
        with fitz.open(pdf_path) as doc:
            sections = TableOfContentsParser.parse_sections(doc)
        selected = TableOfContentsParser.select_sections(sections, spec)
        return selected[0] if selected else None
    except Exception as exc:
        print(f"[warn] could not resolve --section {spec}: {exc}")
        return None


def main() -> int:
    args = build_cli_parser().parse_args()

    section: Optional[SectionRange] = None
    input_dir = args.input_dir

    if args.section is not None:
        section = _resolve_section(args.pdf, args.section)
        if section is None and input_dir is None:
            print("[fail] Section could not be resolved and no --input-dir given; nothing validated.")
            return 0
        if input_dir is None and section is not None:
            input_dir = os.path.join(args.output_dir, section.folder_name)

    if input_dir is None:
        input_dir = args.output_dir

    if args.extract_first:
        if section is None:
            print("[fail] --extract-first requires a resolvable --section; skipping extraction.")
        else:
            print(f"== Extracting section {section.index}: {section.full_title} "
                  f"(pages {section.start_page}-{section.end_page}) -> {input_dir}")
            try:
                FolkStoryPipeline(ExtractorConfig(
                    pdf_path=args.pdf,
                    start_page=section.start_page,
                    end_page=section.end_page,
                    output_dir=input_dir,
                    hard_stops=section.hard_stops + [section.end_page + 1],
                    verbose=args.verbose,
                )).run()
            except Exception as exc:
                print(f"[fail] extraction failed: {exc}")

    if not os.path.isdir(input_dir):
        print(f"[fail] Input directory not found: {input_dir}")
        print("       Re-run with --extract-first to produce it.")
        return 0

    print(f"== Validating {input_dir} (threshold {args.threshold:.2f})")
    try:
        results, section_flags = ExtractionValidator.validate_section(
            pdf_path=args.pdf,
            input_dir=input_dir,
            threshold=args.threshold,
            section=section,
        )
    except Exception as exc:  # never crash: report and exit 0
        print(f"[fail] validation aborted: {exc}")
        return 0

    print(ValidationReporter.render_console(results, section_flags))

    report_path = args.report or os.path.join(input_dir, "validation_report.md")
    try:
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write(ValidationReporter.render_markdown(results, section_flags, args.threshold))
        print(f"Report written: {report_path}")
    except OSError as exc:
        print(f"[fail] could not write report to {report_path}: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
