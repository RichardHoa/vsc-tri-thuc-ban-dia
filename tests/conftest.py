"""
Shared pytest fixtures.

Two kinds of PDF input are used:

* ``data_pdf`` — the real anthology (``data.pdf`` at the repo root), opened once
  per session. Tests against it pin behaviour on known real instances (page 102's
  poem, story 41's dialogue break, the 175→176 footnote continuation, ...).
* ``make_pdf`` — a tiny in-memory PDF built from explicit text items, so a single
  layout feature (a dash at the bottom of a page, an indented italic line, a
  footnote that runs over a page break) can be tested in isolation. Base-14
  fonts are used (``tiro`` = Times-Roman, ``tiit`` = Times-Italic), so synthetic
  text is ASCII only.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import List, Optional

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fitz  # noqa: E402  PyMuPDF

DATA_PDF = os.path.join(ROOT, "data.pdf")

BODY_SIZE = 13.7
FOOTNOTE_SIZE = 11.7
SUPERSCRIPT_SIZE = 7.8


@dataclass
class Item:
    """One line of synthetic text placed at baseline ``(x, y)``."""
    x: float
    y: float
    text: str
    font: str = "tiro"
    size: float = BODY_SIZE


@dataclass
class SyntheticPage:
    items: List[Item]
    # y of a drawn footnote separator rule (None = no rule drawn)
    separator_y: Optional[float] = None


def build_pdf(pages: List[SyntheticPage]) -> "fitz.Document":
    doc = fitz.open()
    for spec in pages:
        page = doc.new_page(width=595, height=842)
        for item in spec.items:
            page.insert_text((item.x, item.y), item.text, fontname=item.font, fontsize=item.size)
        if spec.separator_y is not None:
            page.draw_line((88, spec.separator_y), (250, spec.separator_y))
    # Round-trip through bytes so the document behaves like a file-backed PDF.
    return fitz.open("pdf", doc.tobytes())


@pytest.fixture
def make_pdf():
    opened: List["fitz.Document"] = []

    def _make(pages: List[SyntheticPage]) -> "fitz.Document":
        doc = build_pdf(pages)
        opened.append(doc)
        return doc

    yield _make
    for doc in opened:
        doc.close()


@pytest.fixture(scope="session")
def data_pdf():
    if not os.path.exists(DATA_PDF):
        pytest.skip("data.pdf not available")
    doc = fitz.open(DATA_PDF)
    yield doc
    doc.close()
