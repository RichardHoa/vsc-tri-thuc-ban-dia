"""
Book-level extraction: the Part → Section → leaf layout on disk, the manifests,
and the shared CLI selection rules of the three scripts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from extractor.formatters import TableOfContentsBuilder
from extractor.pipeline import BookPipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PDF = os.path.join(ROOT, "data.pdf")

pytestmark = pytest.mark.usefixtures("data_pdf")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_section_manifest_uses_the_leaf_kind():
    toc = TableOfContentsBuilder.build({"I. X": [{"essay_number": 1}]}, 1, "43 - 58", leaf_key="essays")
    assert toc["total_essays"] == 1
    assert toc["sections"] == [{"section_id": "I", "section_title": "I. X", "essays": [{"essay_number": 1}]}]
    assert "total_stories" not in toc


@pytest.fixture(scope="module")
def part_1_out(tmp_path_factory):
    out = tmp_path_factory.mktemp("book")
    BookPipeline(DATA_PDF, str(out), part=1).run()
    return out


def test_part_1_layout_on_disk(part_1_out):
    part_dir = part_1_out / "PHAN_THU_NHAT"
    assert sorted(os.listdir(part_dir)) == [
        "III_TRUYEN_CO_VIET_NAM_QUA_CAC_THOI_DAI", "II_LAI_LICH_TRUYEN_CO_TICH", "I_BAN_CHAT_TRUYEN_CO_TICH",
    ]
    section = part_dir / "I_BAN_CHAT_TRUYEN_CO_TICH"
    assert sorted(os.listdir(section)) == [f"essay_0{n}.md" for n in range(1, 7)] + ["table_of_contents.json"]
    md = (section / "essay_01.md").read_text(encoding="utf-8")
    assert md.startswith("# I. BẢN CHẤT TRUYỆN CỔ TÍCH\n\n## 1. PHÂN LOẠI TRUYỆN CỔ")
    assert "[^1]: (Trang 43)" in md


def test_part_1_section_manifest(part_1_out):
    toc = _load(part_1_out / "PHAN_THU_NHAT" / "II_LAI_LICH_TRUYEN_CO_TICH" / "table_of_contents.json")
    assert toc["total_essays"] == 5
    [section] = toc["sections"]
    assert section["section_id"] == "II"
    first = section["essays"][0]
    assert set(first) == {"essay_number", "title", "start_page", "end_page", "markdown_file", "footnote_count"}
    assert (first["essay_number"], first["start_page"], first["markdown_file"]) == (1, 59, "essay_01.md")


def test_root_manifest_describes_the_whole_tree(part_1_out):
    root = _load(part_1_out / "table_of_contents.json")
    assert [p["part_id"] for p in root["parts"]] == ["PHAN_THU_NHAT", "PHAN_THU_HAI", "PHAN_THU_BA"]
    part1, part2, part3 = root["parts"]
    assert (part1["start_page"], part1["end_page"], part1["introduction"]) == (42, 84, None)
    assert [s["section_id"] for s in part1["sections"]] == ["I", "II", "III"]
    assert part1["sections"][0]["folder"] == "PHAN_THU_NHAT/I_BAN_CHAT_TRUYEN_CO_TICH"
    assert [len(s["essays"]) for s in part1["sections"]] == [6, 5, 4]
    # Parts not extracted in this run are still described, with no leaves yet.
    assert [s["section_id"] for s in part2["sections"]][:2] == ["I", "II"]
    assert all(s["stories"] == [] for s in part2["sections"])
    assert [s["section_id"] for s in part3["sections"]] == ["IV", "V"]


def test_part_3_introduction_and_sections(tmp_path):
    BookPipeline(DATA_PDF, str(tmp_path), part=3).run()
    part_dir = tmp_path / "PHAN_THU_BA"
    intro = (part_dir / "introduction.md").read_text(encoding="utf-8")
    assert intro.startswith("# PHẦN THỨ BA. NHẬN ĐỊNH TỔNG QUÁT VỀ KHO TÀNG TRUYỆN CỔ TÍCH VIỆT-NAM\n")
    assert "ĐẶC ĐIỂM CỦA TRUYỆN CỔ TÍCH" not in intro
    v = _load(part_dir / "V_THU_TIM_NGUON_GOC_TRUYEN_CO_TICH_VIET_NAM" / "table_of_contents.json")
    assert [(e["essay_number"], e["start_page"]) for e in v["sections"][0]["essays"]] == [
        (1, 1392), (2, 1397), (3, 1413), (4, 1424),
    ]
    root = _load(tmp_path / "table_of_contents.json")
    assert root["parts"][2]["introduction"] == "PHAN_THU_BA/introduction.md"


def test_section_selection_writes_only_that_section(tmp_path):
    BookPipeline(DATA_PDF, str(tmp_path), part=3, section_spec="2").run()
    assert sorted(os.listdir(tmp_path / "PHAN_THU_BA")) == ["V_THU_TIM_NGUON_GOC_TRUYEN_CO_TICH_VIET_NAM"]


def test_story_selection_is_only_for_part_2(tmp_path):
    with pytest.raises(ValueError, match="--story"):
        BookPipeline(DATA_PDF, str(tmp_path), part=1, story_number=3).run()


# --- CLI ---------------------------------------------------------------------


def _cli(script, *args):
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, script), *args],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )


@pytest.mark.parametrize("script", ["extract_folk_stories.py", "survey_data.py", "validate_extraction.py"])
def test_section_without_part_is_rejected(script):
    result = _cli(script, "--section", "2")
    assert result.returncode != 0
    assert "--section requires --part" in result.stderr


def test_list_sections_groups_by_part():
    result = _cli("extract_folk_stories.py", "--list-sections")
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "Part 1: PHẦN THỨ NHẤT" in out and "Part 3: PHẦN THỨ BA" in out
    part3 = out[out.index("Part 3"):]
    assert "1. IV. ĐẶC ĐIỂM CỦA TRUYỆN CỔ TÍCH VIỆT-NAM  (pages 1341-1391)" in part3
    assert "2. V. THỬ TÌM NGUỒN GỐC" in part3
