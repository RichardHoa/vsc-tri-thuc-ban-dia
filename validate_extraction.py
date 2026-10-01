#!/usr/bin/env python3
"""
Extraction Accuracy Validator CLI
---------------------------------
Validates already-extracted folk-story output (``story_NNN.md`` +
``table_of_contents.json``) against data.pdf: structural checks plus a
deterministic difflib text-alignment score, reported worst-first.

Read-only against extraction logic. A reporting tool, not a CI gate: it exits 0
whatever it finds — gaps and failures are reported in the output, never raised.
Only a command-line usage error (e.g. --section without --part) exits non-zero.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

from extractor import (
    BookPipeline,
    ExtractionValidator,
    SectionRange,
    TableOfContentsParser,
    ValidationReporter,
)
from extractor.cli import add_selection_args, check_selection_args


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate extracted folk-story Markdown against data.pdf",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--pdf", default="data.pdf", help="Path to data.pdf")
    add_selection_args(parser)
    parser.add_argument("--output-dir", default="extracted_stories", help="Extraction output root")
    parser.add_argument(
        "--input-dir", default=None,
        help="Explicit Story Section directory holding table_of_contents.json "
             "(overrides --part/--section resolution)",
    )
    parser.add_argument("--threshold", type=float, default=0.90,
                        help="rendered_coverage below this marks a story REVIEW")
    parser.add_argument("--report", default=None,
                        help="Markdown report path (default: <input-dir or output-dir>/validation_report.md)")
    parser.add_argument("--extract-first", action="store_true",
                        help="Run extraction for the selection before validating (opt-in)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return parser


def _resolve_targets(args) -> List[Tuple[str, Optional[SectionRange]]]:
    """(input_dir, section) pairs to validate; [] when nothing resolves."""
    if args.input_dir is not None:
        return [(args.input_dir, None)]
    try:
        with fitz.open(args.pdf) as doc:
            parts = TableOfContentsParser.parse_parts(doc)
        selection = TableOfContentsParser.select_parts(parts, args.part, args.section)
    except Exception as exc:
        print(f"[warn] could not resolve the selection: {exc}")
        return []
    targets = []
    for part, sections in selection:
        if part.leaf_kind != "stories":
            print(f"[skip] Part {part.number} ({part.leaf_kind}): only Story Sections are validated.")
            continue
        targets.extend((os.path.join(args.output_dir, s.path), s) for s in sections)
    return targets


def main() -> int:
    parser = build_cli_parser()
    args = parser.parse_args()
    check_selection_args(parser, args)

    if args.extract_first:
        print(f"== Extracting into {args.output_dir}")
        try:
            BookPipeline(args.pdf, args.output_dir, part=args.part, section_spec=args.section,
                         verbose=args.verbose).run()
        except Exception as exc:
            print(f"[fail] extraction failed: {exc}")

    targets = _resolve_targets(args)
    if not targets:
        print("[fail] Nothing to validate.")
        return 0

    results, section_flags = [], []
    for input_dir, section in targets:
        if not os.path.isdir(input_dir):
            print(f"[fail] Input directory not found: {input_dir}")
            print("       Re-run with --extract-first to produce it.")
            continue
        print(f"== Validating {input_dir} (threshold {args.threshold:.2f})")
        try:
            section_results, flags = ExtractionValidator.validate_section(
                pdf_path=args.pdf,
                input_dir=input_dir,
                threshold=args.threshold,
                section=section,
            )
        except Exception as exc:  # never crash: report and carry on
            print(f"[fail] validation aborted for {input_dir}: {exc}")
            continue
        results.extend(section_results)
        section_flags.extend(flags)

    print(ValidationReporter.render_console(results, section_flags))

    report_path = args.report or os.path.join(args.input_dir or args.output_dir, "validation_report.md")
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
