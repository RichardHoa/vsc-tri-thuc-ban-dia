"""
Story Name Index builder: the printed Bảng tra cứu tên truyện → Index Name
records resolved against the published Story markdown.
"""

from __future__ import annotations

import pytest

from extractor.name_index import build_name_index

PAGE_1 = """
1518
BẢNG TRA CỨU TÊN TRUYỆN KHO TÀNG TRUYỆN CỔ TÍCH VIỆT
NAM

Để ñộc giả tiện tra cứu, ở Bảng tra cứu này chúng tôi sắp xếp theo thứ tự chữ
cái a, b, c. Trường hợp những truyện cùng tên nhưng
khác nội dung, ñể dễ phân biệt, có ghi rõ xuất xứ.

A-ñao dũng cảm
Khảo dị
số
182
tập
V
Ai mua hành tôi hay là lọ
nước thần

số
135
tập
III
"""

PAGE_2 = """
1519
Ba anh em,
truyện Pháp
Khảo dị
số
107
tập
III
Cao phi viễn tẩu
Xem Giáp Kén-xã Nhộng

Chiếc nhẫn thầnChú thích
Khảo dị
số
107
tập
III
Giáp Kén-xã Nhộng

số
135
tập
 III
Không có ñâu cả
Khảo dị
số
182
tập
V
Xử phiến ñá
Khảo dị
số
110
tập
III
Khảo dị
số
120
tập
III
"""

STORIES = {
    "story_107.md": (
        "## 107. Ba chàng thiện nghệ\n\nChàng lặn giỏi kết duyên[^1].\n\n### KHẢO DỊ\n\n"
        "Người Pháp có truyện BA ANH EM: ba anh em ruột muốn lấy một em gái[^1].\n\n"
        "---\n\n### Chú thích\n\n[^1]: (Trang 640) Theo Tân thanh tạp chí\n\n"
        "[^1]: (Trang 641) Xem truyện Chiếc nhẫn thần của người Lào.\n"
    ),
    "story_110.md": "## 110. Tra tấn hòn đá\n\n### KHẢO DỊ\n\nGiống truyện Xử phiến đá trong Bao Công kỳ án.\n",
    "story_120.md": "## 120. Xử kiện\n\n### KHẢO DỊ\n\nXem thêm truyện Xử  phiến - đá ở trên.\n",
    "story_135.md": (
        "## 135. Ai mua hành tôi hay là lọ nước thần\n\n"
        "Giáp Kén-xã Nhộng kể truyện ai mua hành tôi.\n"
    ),
    "story_182.md": "## 182. Truyện\n\n### KHẢO DỊ\n\nTruyện A-dao dũng cảm của người Ba-na. A-dao đi săn.\n",
}


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    root = tmp_path_factory.mktemp("published")
    section = root / "PHAN_THU_HAI" / "VI_TRUYEN_PHAN_XU"
    section.mkdir(parents=True)
    for name, text in STORIES.items():
        (section / name).write_text(text, encoding="utf-8")
    return build_name_index([PAGE_1, PAGE_2], str(root))


def _record(result, printed, qualifier=None):
    matches = [r for r in result.names if r["printed"] == printed and r.get("qualifier") == qualifier]
    assert len(matches) == 1, printed
    return matches[0]


def test_misprinted_name_resolves_to_the_in_text_spelling(result):
    record = _record(result, "A-đao dũng cảm")
    assert record["targets"] == [
        {"story": 182, "tap": "V", "location": "khao-di", "textName": "A-dao dũng cảm"},
    ]


def test_qualifier_is_split_off_the_name(result):
    record = _record(result, "Ba anh em", "truyện Pháp")
    assert record["targets"][0]["textName"] == "BA ANH EM"


def test_wrapped_name_is_joined(result):
    record = _record(result, "Ai mua hành tôi hay là lọ nước thần")
    assert record["targets"] == [
        {"story": 135, "tap": "III", "location": "story", "textName": "Ai mua hành tôi hay là lọ nước thần"},
    ]


def test_xem_alias_copies_the_targets_of_its_name(result):
    alias = _record(result, "Cao phi viễn tẩu")
    assert alias["aliasOf"] == "Giáp Kén-xã Nhộng"
    assert alias["targets"] == _record(result, "Giáp Kén-xã Nhộng")["targets"]
    assert alias["targets"][0]["story"] == 135


def test_nameless_continuation_adds_a_target_to_the_previous_name(result):
    record = _record(result, "Xử phiến đá")
    assert [(t["story"], t["textName"]) for t in record["targets"]] == [
        (110, "Xử phiến đá"), (120, "Xử  phiến - đá"),
    ]


def test_chu_thich_name_records_its_footnote(result):
    target = _record(result, "Chiếc nhẫn thần")["targets"][0]
    assert target == {
        "story": 107, "tap": "III", "location": "chu-thich",
        "textName": "Chiếc nhẫn thần", "footnote": "2",
    }


def test_unresolvable_name_is_reported_and_has_no_text_name(result):
    target = _record(result, "Không có đâu cả")["targets"][0]
    assert "textName" not in target
    assert [(u["printed"], u["story"]) for u in result.unresolved] == [("Không có đâu cả", 182)]
