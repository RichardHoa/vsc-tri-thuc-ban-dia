"""
Essay and Introduction discovery/extraction in the scholarly Parts (1 and 3)
and Part 2's preface.
"""

from __future__ import annotations

import re

import pytest

from extractor import ExtractorConfig, StoryExtractionEngine, Verse
from extractor.discovery import PartLayoutDiscovery
from extractor.normalizer import TextNormalizer
from extractor.toc import TableOfContentsParser


# --- Essay heading recognition --------------------------------------------


@pytest.mark.parametrize("text,expected", [
    ("1. PHÂN LOẠI TRUYỆN CỔ, MỘT VẤN ĐỀ ĐẶT RA TỪ LÂU, NHƯNG VẪN CÒN RẤT MỚI MẺ.",
     (1, "PHÂN LOẠI TRUYỆN CỔ, MỘT VẤN ĐỀ ĐẶT RA TỪ LÂU, NHƯNG VẪN CÒN RẤT MỚI MẺ")),
    ("3.TÍNH CÁCH PHÊ PHÁN HIỆN THỰC", (3, "TÍNH CÁCH PHÊ PHÁN HIỆN THỰC")),
    # A source glitch prints one lower-case letter inside an all-caps heading (p. 1356).
    ("2. TRUYỆN CỔ TÍCH VIỆT-NAM; LÀ BIẾU TRƯNG NGHệ THUẬT",
     (2, "TRUYỆN CỔ TÍCH VIỆT-NAM; LÀ BIẾU TRƯNG NGHệ THUẬT")),
])
def test_essay_heading(text, expected):
    assert PartLayoutDiscovery.parse_essay_heading(text) == expected


@pytest.mark.parametrize("text", [
    "1. Yếu tố tưởng tượng của người Việt-nam trong sáng tác cổ tích gần như ít",
    "1. Truyện cổ tích thần kỳ1.",
    "1. Trong phần kho tàng truyện cổ tích trình bày sau đây, chúng tôi đã gắng",
    "142. Dẫn trong Pu-li-lốp (Poutilov).",
    "IV. ĐẶC ĐIỂM CỦA TRUYỆN CỔ TÍCH VIỆT-NAM",
])
def test_mixed_case_numbered_lines_are_not_essay_headings(text):
    assert PartLayoutDiscovery.parse_essay_heading(text) is None


# --- discovery against data.pdf -------------------------------------------


@pytest.fixture(scope="module")
def parts(data_pdf):
    return TableOfContentsParser.parse_parts(data_pdf)


@pytest.fixture(scope="module")
def layouts(data_pdf, parts):
    return {p.number: PartLayoutDiscovery.discover(data_pdf, p, ExtractorConfig()) for p in parts}


def _muc_luc_essays(data_pdf, part):
    """(number, title, page) of the numbered MỤC LỤC entries inside a Part, in order."""
    out = []
    for e in TableOfContentsParser.parse_entries(data_pdf):
        m = re.match(r'^(\d+)\.\s*(.+)$', e.title)
        if m and part.start_page <= e.page <= part.end_page:
            out.append((int(m.group(1)), m.group(2).rstrip('. '), e.page))
    return out


def test_part_1_essays_match_muc_luc(data_pdf, parts, layouts):
    essays = layouts[1].essays
    assert [len(essays[r]) for r in ("I", "II", "III")] == [6, 5, 4]
    found = [(e.story_number, e.title, e.start_page)
             for r in ("I", "II", "III") for e in essays[r]]
    assert found == _muc_luc_essays(data_pdf, parts[0])


def test_part_3_essays(layouts):
    iv, v = layouts[3].essays["IV"], layouts[3].essays["V"]
    assert [e.story_number for e in iv] == [1, 2, 3, 4]
    assert [e.start_page for e in iv] == [1341, 1356, 1371, 1383]
    # V.1 is printed (non-bold) but missing from MỤC LỤC: the text is the authority.
    assert [e.story_number for e in v] == [1, 2, 3, 4]
    assert [e.start_page for e in v] == [1392, 1397, 1413, 1424]
    assert v[0].title.startswith('CÁC TRƯỜNG PHÁI CỔ TÍCH HỌC XƯA NAY VỚI VẤN ĐỀ CÁI "CHUNG"')
    # The heading wraps over three blocks; all of it is the title.
    assert iv[0].title.endswith("CHIẾM MỘT TỶ LỆ TƯƠNG ĐỐI THẤP")


def test_essays_end_at_the_next_heading(layouts):
    iv, v = layouts[3].essays["IV"], layouts[3].essays["V"]
    # IV.4's closing summary shares p. 1392 with Section V's heading.
    assert iv[-1].end_page == 1392 and iv[-1].body_bottom is not None
    assert v[-1].end_page == 1433
    assert layouts[1].essays["III"][-1].end_page == 84


def test_essay_titles_are_all_caps(layouts):
    for layout in (layouts[1], layouts[3]):
        for essays in layout.essays.values():
            for e in essays:
                assert PartLayoutDiscovery.is_mostly_caps(e.title), e.title


def test_introductions(layouts):
    assert layouts[1].introduction is None
    intro2, intro3 = layouts[2].introduction, layouts[3].introduction
    assert (intro2.start_page, intro2.end_page) == (85, 85)
    assert (intro3.start_page, intro3.end_page) == (1339, 1341)
    # Part 2's preface list is not Stories, and Part 2 has no Essays.
    assert layouts[2].essays == {}


# --- extraction -------------------------------------------------------------


def _plain(paragraphs):
    return [p for p in paragraphs if isinstance(p, str)]


def test_part_3_introduction_stops_at_section_iv(data_pdf, layouts):
    intro = StoryExtractionEngine.extract_single_story(
        data_pdf, layouts[3].introduction, ExtractorConfig())
    text = _plain(intro.paragraphs)
    assert text[0].startswith("Chúng tôi tạm kết thúc công việc dẫn dắt bạn đọc")
    assert text[-1].endswith("xem xét cội nguồn truyện cổ tích Việt-nam.")
    assert not any("ĐẶC ĐIỂM" in p for p in text)
    # p. 1341's footnotes belong to Essay IV.1, whose markers sit below the heading.
    assert intro.footnotes == []


def test_part_2_introduction_keeps_its_numbered_list(data_pdf, layouts):
    intro = StoryExtractionEngine.extract_single_story(
        data_pdf, layouts[2].introduction, ExtractorConfig())
    text = _plain(intro.paragraphs)
    assert text[0].startswith("1. Trong phần kho tàng truyện cổ tích trình bày sau đây")
    assert any(p.startswith("4. Chúng tôi có ý tập hợp") for p in text)
    assert not any("NGUỒN GỐC SỰ VẬT" in p for p in text)


def test_essay_iv_1_body_and_footnote_continued_over_page_break(data_pdf, layouts):
    essay = StoryExtractionEngine.extract_single_story(
        data_pdf, layouts[3].essays["IV"][0], ExtractorConfig())
    text = _plain(essay.paragraphs)
    assert text[0].startswith("Trước khi đề cập đến đặc điểm thứ nhất này")
    assert not any("TỶ LỆ TƯƠNG ĐỐI THẤP" in p for p in text)
    fn = {(f.page, f.orig_num): f for f in essay.footnotes}
    assert (1341, 1) in fn
    assert fn[(1341, 2)].end_page == 1342
    joined = " ".join(text)
    assert "(hay tiểu loại)[^1]" in joined and "thần kỳ[^2]" in joined


def test_essay_iv_4_keeps_summary_but_not_section_v(data_pdf, layouts):
    essay = StoryExtractionEngine.extract_single_story(
        data_pdf, layouts[3].essays["IV"][3], ExtractorConfig())
    text = _plain(essay.paragraphs)
    assert text[-1].endswith("nghĩa, giá trị của truyện cổ tích Việt-nam.")
    assert not any("THỬ TÌM NGUỒN GỐC" in p or "CÁC TRƯỜNG PHÁI" in p for p in text)


def test_essay_v_1_does_not_start_with_its_heading(data_pdf, layouts):
    essay = StoryExtractionEngine.extract_single_story(
        data_pdf, layouts[3].essays["V"][0], ExtractorConfig())
    assert _plain(essay.paragraphs)[0].startswith("Như chúng ta biết, lịch sử bộ môn văn học dân gian")


def test_essay_footnote_verse_renders_as_verse(data_pdf, layouts):
    # Parts 1 and 3 print verse only inside footnotes (p. 1352 here, p. 1379 in IV.3).
    essay = StoryExtractionEngine.extract_single_story(
        data_pdf, layouts[3].essays["IV"][0], ExtractorConfig())
    [fn] = [f for f in essay.footnotes if f.page == 1352 and f.parts]
    assert Verse(["Cái l. tếch nghếch,", "Cái đít choi loi,", "Chổng cho thần coi,", "Để thần phù hộ."]) in fn.parts
