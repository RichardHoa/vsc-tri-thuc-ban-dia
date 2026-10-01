"""
Shared ``--part`` / ``--section`` selection arguments for the three CLI scripts.
"""

from __future__ import annotations

import argparse

SECTION_REQUIRES_PART = "--section requires --part (Section numbering restarts in every Part)."


def add_selection_args(parser: argparse.ArgumentParser) -> None:
    """Adds ``--part N`` and ``--section SPEC``; no selection means all three Parts."""
    parser.add_argument(
        "--part", type=int, choices=[1, 2, 3], default=None,
        help="Part to select (1 and 3: Essays, 2: Stories). Default: all three Parts",
    )
    parser.add_argument(
        "--section", default=None,
        help="Section(s) within --part by 1-based MỤC LỤC index, e.g. 1, 1-3 or 1,4. Requires --part",
    )


def check_selection_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Exits non-zero (argparse usage error) on ``--section`` without ``--part``."""
    if args.section is not None and args.part is None:
        parser.error(SECTION_REQUIRES_PART)
