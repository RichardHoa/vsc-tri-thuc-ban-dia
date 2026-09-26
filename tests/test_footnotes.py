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


def test_continuation_is_merged_into_the_footnote_it_continues(make_pdf):
    doc = _two_page_doc(make_pdf)
    _, notes = FootnoteEngine.collect_story_footnotes(doc, 1, 2, ExtractorConfig())
    assert [(f.orig_num, f.page, f.end_page) for f in notes] == [
        (1, 1, 1),
        (2, 1, 2),
        (1, 2, 2),
    ]
    assert notes[1].text == "Second note begins and carries on over the page."


def test_continuation_on_first_page_looks_at_page_before_range(make_pdf):
    doc = _two_page_doc(make_pdf)
    _, notes = FootnoteEngine.collect_story_footnotes(doc, 2, 2, ExtractorConfig())
    # the note it continues lies before the story's range: kept as its own entry
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


def test_real_page_175_176_footnote_2_is_one_merged_entry(data_pdf):
    _, notes = FootnoteEngine.collect_story_footnotes(data_pdf, 175, 176, ExtractorConfig())
    two = [f for f in notes if f.orig_num == 2]
    assert len(two) == 1
    assert (two[0].page, two[0].end_page) == (175, 176)
    assert two[0].text.startswith("Xem thêm Lược khảo")
    assert "Truyện bà mẹ Mục Liên" in two[0].text


def test_real_page_240_241_verse_couplet_is_merged(data_pdf):
    _, notes = FootnoteEngine.collect_story_footnotes(data_pdf, 240, 241, ExtractorConfig())
    four = [f for f in notes if f.orig_num == 4]
    assert len(four) == 1 and (four[0].page, four[0].end_page) == (240, 241)
    assert four[0].parts[-1] == Verse(
        ["Đôi ta như chim tử quy.", "Đêm nghe thấy tiếng, ngày đi phương nào."]
    )
    assert [f.orig_num for f in notes if f.page == 241] == [1, 2]


def test_parse_number_glued_to_text_is_split():
    # page 536 prints "2Theo Truyện dân gian Miến-điện" (no space after the number)
    entries = FootnoteEngine.parse_footnote_text("1 Theo A. 2Theo B. 3 Theo C.", 536)
    assert [(e["orig_num"], e["text"]) for e in entries] == [
        (1, "Theo A."), (2, "Theo B."), (3, "Theo C."),
    ]


def test_real_page_536_three_footnotes(data_pdf):
    _, notes = FootnoteEngine.collect_story_footnotes(data_pdf, 536, 536, ExtractorConfig())
    assert [f.orig_num for f in notes] == [1, 2, 3]
    assert notes[1].text.startswith("Theo Truyện dân gian Miến-điện")


def test_parse_doubled_footnote_number_is_read_as_expected_number():
    # pages 607 ("33 Theo lời kể") and 609/611/612 ("11 Đoạn này") print the
    # footnote number doubled; the body marker is the single number.
    entries = FootnoteEngine.parse_footnote_text("1 Theo A. 2 Theo B. 33 Theo C.", 607)
    assert [e["orig_num"] for e in entries] == [1, 2, 3]
    assert entries[2]["text"] == "Theo C."
    entries = FootnoteEngine.parse_footnote_text("11 Đoạn này theo Nguyễn Bính.", 609)
    assert [(e["orig_num"], e["text"]) for e in entries] == [(1, "Đoạn này theo Nguyễn Bính.")]


def test_parse_empty_footnote_does_not_swallow_the_next_number():
    # page 601 prints footnote 1 with no text, then "2 Theo Phan Kế Bính ..."
    entries = FootnoteEngine.parse_footnote_text("1 2 Theo Phan Kế Bính.", 601)
    assert [(e["orig_num"], e["text"]) for e in entries] == [(1, ""), (2, "Theo Phan Kế Bính.")]


def test_real_pages_601_607_609(data_pdf):
    cfg = ExtractorConfig()
    _, n601 = FootnoteEngine.collect_story_footnotes(data_pdf, 601, 601, cfg)
    assert [(f.orig_num, f.text[:9]) for f in n601] == [(1, ""), (2, "Theo Phan")]
    _, n607 = FootnoteEngine.collect_story_footnotes(data_pdf, 607, 607, cfg)
    assert [f.orig_num for f in n607] == [1, 2, 3]
    _, n609 = FootnoteEngine.collect_story_footnotes(data_pdf, 609, 609, cfg)
    assert [f.orig_num for f in n609] == [1]


def test_parse_number_inside_parentheses_is_not_a_new_footnote():
    # page 1203: footnote 1 says "(1. Người chồng hóa nai; 2. Trộm áo nàng tiên)"
    text = ("1 Theo Nàng Át Kao. Trong Truyện cổ Dao thì người kể chia làm hai truyện "
            "(1. Người chồng hóa nai; 2. Trộm áo nàng tiên) tuy có nhiều tình tiết mới.")
    entries = FootnoteEngine.parse_footnote_text(text, 1203)
    assert len(entries) == 1
    assert entries[0]["text"].endswith("tuy có nhiều tình tiết mới.")


def test_parse_after_closed_parentheses_still_splits():
    entries = FootnoteEngine.parse_footnote_text("1 Theo A (1924). 2 Theo B.", 5)
    assert [e["orig_num"] for e in entries] == [1, 2]


def test_real_page_1203_single_footnote(data_pdf):
    _, notes = FootnoteEngine.collect_story_footnotes(data_pdf, 1203, 1203, ExtractorConfig())
    assert [f.orig_num for f in notes] == [1]
    assert "2. Trộm áo nàng tiên" in notes[0].text
