"""Verse-line detection (italic font + indentation / short italic margin runs)."""

from __future__ import annotations

from conftest import BODY_SIZE, FOOTNOTE_SIZE, Item, SyntheticPage

from extractor.models import ExtractorConfig
from extractor.verse import VerseDetector


def _lines(doc, pno=0):
    blocks = [b for b in doc[pno].get_text("dict")["blocks"] if b.get("type") == 0]
    blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
    VerseDetector.mark_verse_lines(blocks, ExtractorConfig())
    out = []
    for b in blocks:
        for line in b["lines"]:
            out.append(("".join(s["text"] for s in line["spans"]).strip(), line["is_verse"]))
    return out


def test_italic_font_names():
    assert VerseDetector.is_italic_font("Times-Italic")
    assert VerseDetector.is_italic_font("TimesNewRoman,Italic")
    assert VerseDetector.is_italic_font("Times-BoldItalic")
    assert VerseDetector.is_italic_font("Helvetica-Oblique")
    assert not VerseDetector.is_italic_font("Times-Roman")
    assert not VerseDetector.is_italic_font("TimesNewRoman")


def test_indented_italic_lines_are_verse(make_pdf):
    doc = make_pdf([SyntheticPage([
        Item(88, 100, "The bird cried out:"),
        Item(280, 130, "Cuckoo cuckoo.", "tiit"),
        Item(283, 150, "Rice is ripe,", "tiit"),
        Item(99, 180, "After that it flew away."),
    ])])
    assert _lines(doc) == [
        ("The bird cried out:", False),
        ("Cuckoo cuckoo.", True),
        ("Rice is ripe,", True),
        ("After that it flew away.", False),
    ]


def test_indented_roman_line_is_not_verse(make_pdf):
    doc = make_pdf([SyntheticPage([Item(280, 130, "Not italic at all.")])])
    assert _lines(doc) == [("Not italic at all.", False)]


def test_all_caps_italic_heading_is_not_verse(make_pdf):
    doc = make_pdf([SyntheticPage([Item(286, 130, "KHAO DI", "tiit")])])
    assert _lines(doc) == [("KHAO DI", False)]


def test_single_short_italic_margin_line_is_not_verse(make_pdf):
    # e.g. the italic tail of a wrapped book-title citation
    doc = make_pdf([SyntheticPage([
        Item(88, 100, "Some prose that cites a book called"),
        Item(88, 120, "Old Tales.", "tiit"),
        Item(88, 140, "And the prose goes on."),
    ])])
    assert [v for _, v in _lines(doc)] == [False, False, False]


def test_run_of_short_italic_margin_lines_is_verse(make_pdf):
    doc = make_pdf([SyntheticPage([
        Item(88, 100, "The original text reads:"),
        Item(88, 120, "Meet a shrine, do not sleep,", "tiit"),
        Item(88, 140, "Meet a bath, do not bathe,", "tiit"),
        Item(88, 160, "And so it ends."),
    ])])
    assert [v for _, v in _lines(doc)] == [False, True, True, False]


def test_numbered_italic_margin_lines_are_not_verse(make_pdf):
    # footnote entries whose whole citation is an italic book title
    doc = make_pdf([SyntheticPage([
        Item(88, 700, "2 Dong-duong Review (1904).", "tiit", FOOTNOTE_SIZE),
        Item(88, 715, "3 Report of Quang-lang.", "tiit", FOOTNOTE_SIZE),
    ])])
    assert [v for _, v in _lines(doc)] == [False, False]


def test_superscript_digit_does_not_count_against_italic_ratio(make_pdf):
    doc = make_pdf([SyntheticPage([
        Item(273, 130, "Fly home and eat!", "tiit", BODY_SIZE),
        Item(380, 125, "2", "tiro", 7.8),
    ])])
    flags = dict(_lines(doc))
    assert flags["Fly home and eat!"] is True


def test_real_page_102_poem(data_pdf):
    verse = [t for t, v in _lines(data_pdf, 101) if v]
    assert len(verse) == 4
    assert verse[0].startswith("Cô hố cô hố")
    assert verse[-1].startswith("Bay về mà ăn")


def test_real_page_909_margin_footnote_poem(data_pdf):
    verse = [t for t, v in _lines(data_pdf, 908) if v]
    assert len(verse) == 4
    assert verse[0].startswith("Phùng")
