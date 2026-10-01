"""Validator over every leaf kind: page-aware orphan checks, Essays and
Introductions, the MỤC LỤC erratum and the Part → Section report."""

from __future__ import annotations

import json
import re

import pytest

from extractor.discovery import PartLayoutDiscovery, StoryDiscoveryEngine
from extractor.engine import StoryExtractionEngine
from extractor.formatters import MarkdownRenderer
from extractor.models import ExtractorConfig
from extractor.toc import TableOfContentsParser
from extractor.validation import (
    ExtractionValidator,
    LeafJob,
    StoryValidationResult,
    ValidationReporter,
    check_completeness,
    check_orphans,
    check_structure,
    strip_markers,
)


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


# --- page-aware orphan check --------------------------------------------------


def test_missing_marker_is_not_hidden_by_same_number_on_another_page():
    # Story 25 before the heading fix: p. 199's [^1] was dropped from the heading.
    markers = [(201, 1), (202, 1), (203, 1)]
    footnotes = [(1, 199, 199), (1, 201, 201), (1, 202, 202), (1, 203, 203)]
    assert check_orphans(markers, footnotes) == ["ORPHAN_FOOTNOTE:1@199"]


def test_marker_without_definition_on_its_page():
    assert check_orphans([(357, 2), (357, 3)], [(2, 357, 357)]) == ["ORPHAN_MARKER:3@357"]


def test_merged_footnote_is_matched_on_its_first_page():
    assert check_orphans([(175, 2)], [(2, 175, 176)]) == []


def test_unlocated_marker_matches_by_number():
    assert check_orphans([(None, 1)], [(1, 12, 12)]) == []
    assert check_orphans([(None, 2)], [(1, 12, 12)]) == ["ORPHAN_MARKER:2", "ORPHAN_FOOTNOTE:1@12"]


def test_footnote_without_page_matches_by_number():
    assert check_orphans([(12, 1)], [(1, -1, -1)]) == []


def test_strip_markers_reports_offsets_in_normalized_text():
    text, offsets = strip_markers("SỰ TÍCH  CÁ HE[^1] và\nTHÔI SINH [^2] x")
    assert text == "SỰ TÍCH CÁ HE và THÔI SINH x"
    assert [(text[:o], n) for o, n in offsets] == [("SỰ TÍCH CÁ HE", 1), ("SỰ TÍCH CÁ HE và THÔI SINH ", 2)]


@pytest.fixture(scope="module")
def story_25_md(data_pdf):
    story = {s.story_number: s for s in StoryDiscoveryEngine.discover_stories(data_pdf, 199, 203)}[25]
    content = StoryExtractionEngine.extract_single_story(data_pdf, story, ExtractorConfig())
    return MarkdownRenderer.render(content)


def _validate_story(tmp_path, data_pdf, md):
    toc = {"sections": [{"section_id": "I", "stories": [{
        "story_number": 25, "title": "T", "start_page": 199, "end_page": 203,
        "markdown_file": "story_025.md", "footnote_count": None,
    }]}]}
    _write(tmp_path, "table_of_contents.json", json.dumps(toc))
    _write(tmp_path, "story_025.md", md)
    results, _, _ = ExtractionValidator.validate_section(data_pdf.name, str(tmp_path))
    return results[0]


def test_real_story_25_heading_marker_is_matched(tmp_path, data_pdf, story_25_md):
    assert "THÁC ĐAO[^1] HAY" in story_25_md
    result = _validate_story(tmp_path, data_pdf, story_25_md)
    assert not [f for f in result.structural_flags if f.startswith("ORPHAN")]
    assert result.rendered_coverage == pytest.approx(1.0)


def test_real_story_25_without_heading_marker_flags_page_199(tmp_path, data_pdf, story_25_md):
    pre_fix = story_25_md.replace("THÁC ĐAO[^1] HAY", "THÁC ĐAO HAY")
    result = _validate_story(tmp_path, data_pdf, pre_fix)
    assert [f for f in result.structural_flags if f.startswith("ORPHAN")] == ["ORPHAN_FOOTNOTE:1@199"]


# --- Essays and Introductions ----------------------------------------------


def test_essay_section_is_validated_as_essays(tmp_path, data_pdf):
    toc = {"sections": [{"section_id": "V", "section_title": "V. X", "essays": [{
        "essay_number": 1, "title": "T", "start_page": 1392, "end_page": 1392,
        "markdown_file": "essay_01.md", "footnote_count": None,
    }]}]}
    _write(tmp_path, "table_of_contents.json", json.dumps(toc))
    _write(tmp_path, "essay_01.md", "# V. X\n\n## 1. T\n\nx.\n")
    results, _, _ = ExtractionValidator.validate_section(data_pdf.name, str(tmp_path))
    assert [(r.kind, r.label) for r in results] == [("essay", "Essay V.1")]


def test_a_leaf_that_fails_is_reported_not_raised(tmp_path, data_pdf):
    _write(tmp_path, "story_001.md", "")
    (tmp_path / "story_001.md").write_bytes(b"# C\n\n## 1. T\n\n\xff\xfe bad utf-8\n")
    job = LeafJob(kind="story", number=1, title="T", label="", md_path=str(tmp_path / "story_001.md"),
                  start_page=100, end_page=100, toc_entry={}, errata_key=1)
    [result] = ExtractionValidator.validate_leaves(data_pdf.name, [job])
    assert result.status == "REVIEW"
    assert result.structural_flags[0].startswith("VALIDATION_ERROR")


def test_introduction_has_no_title_to_check():
    parsed = {"title": "", "category": "PHẦN THỨ BA", "body": "x.", "footnotes": [],
              "footnote_entries": []}
    assert "EMPTY_TITLE" not in check_structure(parsed, {}, require_title=False)[0]
    assert "EMPTY_TITLE" in check_structure(parsed, {})[0]


# --- MỤC LỤC erratum ----------------------------------------------------------


@pytest.fixture(scope="module")
def part_3(data_pdf):
    return next(p for p in TableOfContentsParser.parse_parts(data_pdf) if p.number == 3)


def test_part_3_section_v_count_drift_is_a_muc_luc_erratum(data_pdf, part_3):
    section_v = next(s for s in part_3.sections if s.roman == "V")
    flags, errata = check_completeness(data_pdf, section_v, [1, 2, 3, 4], leaf_kind="essays")
    assert flags == []
    assert len(errata) == 1 and errata[0].startswith("EXTRA_ESSAYS")


def test_part_3_section_v_other_drift_is_still_flagged(data_pdf, part_3):
    section_v = next(s for s in part_3.sections if s.roman == "V")
    flags, errata = check_completeness(data_pdf, section_v, [1, 2, 3, 4, 5], leaf_kind="essays")
    assert errata == [] and flags and flags[0].startswith("EXTRA_ESSAYS")


# --- report ---------------------------------------------------------------------


def _result(**kw):
    base = dict(story_number=1, title="T", markdown_file="f.md", start_page=1, end_page=2,
                rendered_coverage=1.0, raw_coverage=1.0, char_per_page=2000.0)
    base.update(kw)
    return StoryValidationResult(**base)


def test_report_groups_non_ok_leaves_by_part_then_section():
    results = [
        _result(story_number=13, part="PHẦN THỨ HAI", section="I. A", structural_flags=["X"]),
        _result(story_number=14, part="PHẦN THỨ HAI", section="I. A"),
        _result(story_number=0, kind="introduction", label="Introduction", part="PHẦN THỨ BA",
                section="", structural_flags=["Y"]),
        _result(story_number=1, kind="essay", label="Essay V.1", part="PHẦN THỨ BA",
                section="V. B", source_errata=["Z — typo"]),
    ]
    md = ValidationReporter.render_markdown(results, [], section_errata=["EXTRA_ESSAYS — omitted"])
    grouped = md.split("## Flagged by Part and Section")[1].split("\n## ")[0]
    order = [line for line in grouped.splitlines() if line.startswith(("###", "- "))]
    assert order == [
        "### PHẦN THỨ HAI",
        "#### I. A",
        "- **Story 13** — T (`f.md`, pp. 1-2): REVIEW — X",
        "### PHẦN THỨ BA",
        "- **Introduction** — T (`f.md`, pp. 1-2): REVIEW — Y",
        "#### V. B",
        "- **Essay V.1** — T (`f.md`, pp. 1-2): ERRATUM — Z",
    ]
    assert "EXTRA_ESSAYS — omitted" in md
    assert not re.search(r"Story 14\*\*", grouped)


# --- selection and Introductions end to end --------------------------------


def test_collect_selects_introductions_and_sections(tmp_path, data_pdf, part_3):
    (tmp_path / "PHAN_THU_BA").mkdir()
    _write(tmp_path / "PHAN_THU_BA", "introduction.md", "# P\n\nx.\n")

    jobs, flags, _ = ExtractionValidator.collect(data_pdf, str(tmp_path), part=3)
    assert [(j.kind, j.start_page, j.end_page) for j in jobs] == [
        ("introduction", part_3.start_page, part_3.sections[0].start_page)]
    assert [f.split(":")[0] for f in flags] == ["MISSING_SECTION"] * 2

    jobs, flags, _ = ExtractionValidator.collect(data_pdf, str(tmp_path), part=3, section_spec="2")
    assert jobs == [] and len(flags) == 1 and "PHAN_THU_BA/V_" in flags[0]

    jobs, flags, _ = ExtractionValidator.collect(data_pdf, str(tmp_path))
    assert [j.errata_key for j in jobs] == ["Introduction PHAN_THU_BA"]
    assert len(flags) == 3 + 10 + 2  # every Section of all three Parts


def test_real_part_3_introduction_validates(tmp_path, data_pdf, part_3):
    config = ExtractorConfig()
    intro = PartLayoutDiscovery.discover(data_pdf, part_3, config).introduction
    content = StoryExtractionEngine.extract_single_story(data_pdf, intro, config)
    (tmp_path / part_3.folder_name).mkdir()
    _write(tmp_path / part_3.folder_name, "introduction.md", MarkdownRenderer.render(content))

    job = ExtractionValidator.introduction_job(str(tmp_path), part_3, "introduction.md")
    [result] = ExtractionValidator.validate_leaves(data_pdf.name, [job])
    assert (result.kind, result.display_label) == ("introduction", "Introduction")
    assert "EMPTY_TITLE" not in result.structural_flags
    assert result.rendered_coverage == pytest.approx(1.0)


def test_parallel_results_keep_job_order(tmp_path, data_pdf):
    jobs = []
    for number, size in ((1, 1), (2, 40)):  # the larger leaf is scheduled first
        name = f"story_00{number}.md"
        _write(tmp_path, name, f"# C\n\n## {number}. T\n\n" + "x. " * size + "\n")
        jobs.append(LeafJob(kind="story", number=number, title="T", label="",
                            md_path=str(tmp_path / name), start_page=100, end_page=100,
                            toc_entry={}, errata_key=number))
    results = ExtractionValidator.validate_leaves(data_pdf.name, jobs, workers=2)
    assert [r.story_number for r in results] == [1, 2]
