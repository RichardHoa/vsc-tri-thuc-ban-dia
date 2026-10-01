#!/usr/bin/env python3
"""
Extraction Accuracy Validator CLI
---------------------------------
Validates already-extracted output (Stories, Essays and Introductions, with
their ``table_of_contents.json`` manifests) against data.pdf: structural checks
plus a deterministic difflib text-alignment score. No selection validates all
three Parts into one report, grouped Part → Section.

Read-only against extraction logic. A reporting tool, not a CI gate: it exits 0
whatever it finds — gaps and failures are reported in the output, never raised.
Only a command-line usage error (e.g. --section without --part) exits non-zero.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple

import fitz  # PyMuPDF

from extractor import (
    BookPipeline,
    ExtractionValidator,
    LeafJob,
    ValidationReporter,
)
from extractor.cli import add_selection_args, check_selection_args


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate extracted Markdown against data.pdf",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--pdf", default="data.pdf", help="Path to data.pdf")
    add_selection_args(parser)
    parser.add_argument("--output-dir", default="extracted_stories", help="Extraction output root")
    parser.add_argument(
        "--input-dir", default=None,
        help="Explicit Section directory holding table_of_contents.json "
             "(overrides --part/--section resolution)",
    )
    parser.add_argument("--threshold", type=float, default=0.90,
                        help="rendered_coverage below this marks a leaf REVIEW")
    parser.add_argument("--report", default=None,
                        help="Markdown report path (default: <input-dir or output-dir>/validation_report.md)")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1,
                        help="Parallel processes scoring leaves")
    parser.add_argument("--extract-first", action="store_true",
                        help="Run extraction for the selection before validating (opt-in)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return parser


def _collect(args) -> Tuple[List[LeafJob], List[str], List[str]]:
    """``(jobs, section_flags, section_errata)`` for the selection, in book order."""
    if not os.path.exists(args.pdf):
        if args.input_dir is not None:  # still checkable structurally, without scores
            jobs, flags = ExtractionValidator.section_jobs(args.input_dir)
            return jobs, flags + [f"MISSING_PDF: {args.pdf} not found — alignment scoring skipped"], []
        print(f"[warn] {args.pdf} not found: MỤC LỤC is needed to resolve the selection")
        return [], [], []
    try:
        with fitz.open(args.pdf) as doc:
            if args.input_dir is not None:
                return ExtractionValidator.collect_section(doc, args.input_dir)
            return ExtractionValidator.collect(doc, args.output_dir, args.part, args.section)
    except Exception as exc:
        print(f"[warn] could not resolve the selection: {exc}")
        return [], [], []


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

    jobs, section_flags, section_errata = _collect(args)
    if not jobs:
        for flag in section_flags:
            print(f"[fail] {flag}")
        print("[fail] Nothing to validate.")
        return 0

    print(f"== Validating {len(jobs)} leaves with {args.workers} workers "
          f"(threshold {args.threshold:.2f})")
    try:
        results = ExtractionValidator.validate_leaves(args.pdf, jobs, args.threshold, args.workers)
    except Exception as exc:  # never crash: report and carry on
        print(f"[fail] validation aborted: {exc}")
        return 0

    print(ValidationReporter.render_console(results, section_flags))

    report_path = args.report or os.path.join(args.input_dir or args.output_dir, "validation_report.md")
    try:
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write(ValidationReporter.render_markdown(
                results, section_flags, args.threshold, section_errata))
        print(f"Report written: {report_path}")
    except OSError as exc:
        print(f"[fail] could not write report to {report_path}: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
