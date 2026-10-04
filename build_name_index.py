#!/usr/bin/env python3
"""
Story Name Index builder (one-off)
----------------------------------
Reads the printed Bảng tra cứu tên truyện (PDF pages 1518–1551), resolves each
Index Name against the website's published Story markdown, and writes the
editable index JSON into that published data, plus a report of the names it
could not resolve.

The JSON is the source of truth once written: the maintainer fixes unresolved
records by hand, and re-running this script overwrites those fixes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

import fitz  # PyMuPDF

from extractor.name_index import build_name_index

INDEX_FIRST_PAGE = 1518
INDEX_LAST_PAGE = 1551
INDEX_FILENAME = "story_name_index.json"
DEFAULT_REPORT = ".scratch/kho-tang-preface-and-name-index/unresolved-index-names.md"


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the Story Name Index JSON from data.pdf's Bảng tra cứu tên truyện",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--pdf", default="data.pdf", help="Path to data.pdf")
    parser.add_argument("--data-dir", required=True,
                        help="The website's published Kho Tàng data folder "
                             "(public/data/kho-tang-truyen-co-tich-viet-nam); read for Story "
                             f"markdown and written to as {INDEX_FILENAME}")
    parser.add_argument("--report", default=DEFAULT_REPORT, help="Unresolved-names report (Markdown)")
    return parser


def write_report(path: str, unresolved: list, fuzzy: list, summary: str) -> None:
    lines = ["# Unresolved Story Name Index entries", "", summary, "",
             f"Fix each by hand in `{INDEX_FILENAME}` (set the target's `textName`, "
             "and `footnote` for Chú thích targets).", "",
             "| Printed name | Qualifier | Story | Location | Reason |",
             "|---|---|---|---|---|"]
    for u in unresolved:
        lines.append(f"| {u['printed']} | {u['qualifier'] or ''} | {u['story'] or ''} "
                     f"| {u['location'] or ''} | {u['reason']} |")
    lines += ["", "## Resolved by fuzzy match", "",
              "Check each in-text spelling is really the same tale; fix or remove `textName` if not.", "",
              "| Printed name | Qualifier | Story | Location | In-text spelling |",
              "|---|---|---|---|---|"]
    for row in fuzzy:
        lines.append(f"| {row['printed']} | {row['qualifier'] or ''} | {row['story']} "
                     f"| {row['location']} | {row['textName']} |")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    args = build_cli_parser().parse_args()
    try:
        with fitz.open(args.pdf) as doc:
            pages = [doc[p - 1].get_text() for p in range(INDEX_FIRST_PAGE, INDEX_LAST_PAGE + 1)]
        result = build_name_index(pages, args.data_dir)

        output = os.path.join(args.data_dir, INDEX_FILENAME)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result.names, f, ensure_ascii=False, indent=2)
            f.write("\n")

        targets = [t for r in result.names if "aliasOf" not in r for t in r["targets"]]
        by_location = Counter(t["location"] for t in targets)
        summary = (f"{len(result.names)} Index Names "
                   f"({sum('aliasOf' in r for r in result.names)} Xem aliases), "
                   f"{len(targets)} targets ({by_location['story']} story, "
                   f"{by_location['khao-di']} khao-di, {by_location['chu-thich']} chu-thich); "
                   f"{len(result.unresolved)} unresolved.")
        summary += f" {len(result.fuzzy)} resolved only by fuzzy match."
        write_report(args.report, result.unresolved, result.fuzzy, summary)

        print(f"Wrote {output}")
        print(summary)
        for u in result.unresolved:
            qualifier = f", {u['qualifier']}" if u["qualifier"] else ""
            print(f"  UNRESOLVED {u['printed']}{qualifier} → {u['story']} ({u['location']}): {u['reason']}")
        print(f"Report: {args.report}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
