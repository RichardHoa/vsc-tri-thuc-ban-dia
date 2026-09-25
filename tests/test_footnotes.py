"""Footnote parsing: continuation text that runs over a page break keeps its number."""

from __future__ import annotations

from conftest import FOOTNOTE_SIZE, Item, SyntheticPage

from extractor.footnotes import FootnoteEngine
from extractor.models import ExtractorConfig, Verse


def test_parse_keeps_leading_continuation_text():
    entries = FootnoteEngine.parse_footnote_text("continued from before. 1 Theo Sach A.", 12)
    assert entries[0]["continued"] is True
    assert entries[0]["text"] == "continued from before."
    assert entries[1]["orig_num"] == 1
    assert entries[1]["continued"] is False
    assert entries[1]["text"] == "Theo Sach A."


def test_parse_numbered_only_is_not_continued():
    entries = FootnoteEngine.parse_footnote_text("1 Theo Sach A. 2 Theo Sach B.", 12)
    assert [(e["orig_num"], e["continued"]) for e in entries] == [(1, False), (2, False)]


def test_parse_unnumbered_only_is_continued():
    entries = FootnoteEngine.parse_footnote_text("Giang-mia sau mot cuoc di buon xa ve.", 12)
    assert len(entries) == 1
    assert entries[0]["continued"] is True


def _two_page_doc(make_pdf):
    return make_pdf([
        SyntheticPage([
            Item(88, 100, "Body text one."),
            Item(88, 705, "1 First note.", size=FOOTNOTE_SIZE),
            Item(88, 720, "2 Second note begins and", size=FOOTNOTE_SIZE),
        ], separator_y=690),
        SyntheticPage([
            Item(88, 100, "Body text two."),
            Item(88, 705, "carries on over the page.", size=FOOTNOTE_SIZE),
            Item(88, 720, "1 Another note.", size=FOOTNOTE_SIZE),
        ], separator_y=690),
    ])


def test_continuation_inherits_previous_pages_last_number(make_pdf):
    doc = _two_page_doc(make_pdf)
    _, notes = FootnoteEngine.collect_story_footnotes(doc, 1, 2, ExtractorConfig())
    assert [(f.orig_num, f.page, f.continued) for f in notes] == [
        (1, 1, False),
        (2, 1, False),
        (2, 2, True),
        (1, 2, False),
    ]
    assert notes[2].text == "carries on over the page."


def test_continuation_on_first_page_looks_at_page_before_range(make_pdf):
    doc = _two_page_doc(make_pdf)
    _, notes = FootnoteEngine.collect_story_footnotes(doc, 2, 2, ExtractorConfig())
    assert [(f.orig_num, f.page, f.continued) for f in notes] == [(2, 2, True), (1, 2, False)]


def test_unnumbered_footer_without_previous_footnotes_falls_back_to_1(make_pdf):
    doc = make_pdf([
        SyntheticPage([Item(88, 100, "Body.")]),
        SyntheticPage([
            Item(88, 100, "Body."),
            Item(88, 705, "Stray footer text.", size=FOOTNOTE_SIZE),
        ], separator_y=690),
    ])
    _, notes = FootnoteEngine.collect_story_footnotes(doc, 1, 2, ExtractorConfig())
    assert [(f.orig_num, f.page, f.continued) for f in notes] == [(1, 2, False)]


def test_footnote_verse_is_kept_as_verse_part(make_pdf):
    doc = make_pdf([SyntheticPage([
        Item(88, 100, "Body."),
        Item(88, 705, "1 A folk song says:", size=FOOTNOTE_SIZE),
        Item(253, 720, "Two of us like birds.", "tiit", FOOTNOTE_SIZE),
        Item(88, 735, "2 Theo Sach B.", size=FOOTNOTE_SIZE),
    ], separator_y=690)])
    _, notes = FootnoteEngine.collect_story_footnotes(doc, 1, 1, ExtractorConfig())
    assert notes[0].orig_num == 1
    assert notes[0].parts == ["A folk song says:", Verse(["Two of us like birds."])]
    assert notes[0].text == "A folk song says: Two of us like birds."
    assert notes[1].parts == []
    assert notes[1].text == "Theo Sach B."


def test_real_page_176_continues_footnote_2_of_page_175(data_pdf):
    _, notes = FootnoteEngine.collect_story_footnotes(data_pdf, 175, 176, ExtractorConfig())
    on_176 = [f for f in notes if f.page == 176]
    assert on_176[0].orig_num == 2
    assert on_176[0].continued is True
    assert on_176[0].text.startswith("Truyện bà mẹ Mục Liên")


def test_real_page_241_continuation_verse_is_no_longer_dropped(data_pdf):
    _, notes = FootnoteEngine.collect_story_footnotes(data_pdf, 240, 241, ExtractorConfig())
    four_240 = [f for f in notes if f.page == 240 and f.orig_num == 4][0]
    assert four_240.parts[-1] == Verse(["Đôi ta như chim tử quy."])
    on_241 = [f for f in notes if f.page == 241]
    assert (on_241[0].orig_num, on_241[0].continued) == (4, True)
    assert on_241[0].parts == [Verse(["Đêm nghe thấy tiếng, ngày đi phương nào."])]
    assert [f.orig_num for f in on_241[1:]] == [1, 2]
