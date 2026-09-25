"""Edge-case survey: poem runs, dialogue page-boundary breaks, footnote chains."""

from __future__ import annotations

import os
import subprocess
import sys

from conftest import FOOTNOTE_SIZE, ROOT, Item, SyntheticPage

from extractor.models import ExtractorConfig
from extractor.survey import EdgeCaseSurvey, FootnoteChain

CFG = ExtractorConfig()


def test_dialogue_break_at_page_end(make_pdf):
    doc = make_pdf([SyntheticPage([
        Item(99, 100, "Narrative."),
        Item(88, 650, "Ngoc hoi: -"),
        Item(88, 705, "1 Theo A.", size=FOOTNOTE_SIZE),
    ], separator_y=690)])
    breaks = EdgeCaseSurvey.find_dialogue_breaks(doc[0], 1, CFG)
    assert [(b.page, b.kind) for b in breaks] == [(1, "page_end")]
    assert breaks[0].text.endswith("hoi: -")


def test_hyphenated_word_at_line_end_is_not_a_break(make_pdf):
    doc = make_pdf([SyntheticPage([Item(88, 650, "Theo Co-")])])
    assert EdgeCaseSurvey.find_dialogue_breaks(doc[0], 1, CFG) == []


def test_dialogue_break_at_block_end_mid_page(make_pdf):
    doc = make_pdf([SyntheticPage([
        Item(99, 100, "He asked: -"),
        Item(99, 300, "Something else entirely."),
    ])])
    assert [b.kind for b in EdgeCaseSurvey.find_dialogue_breaks(doc[0], 1, CFG)] == ["block_end"]


def test_poem_runs_body_and_footnote(make_pdf):
    doc = make_pdf([SyntheticPage([
        Item(99, 100, "He sang:"),
        Item(280, 130, "Line one,", "tiit"),
        Item(280, 150, "Line two.", "tiit"),
        Item(88, 705, "1 A song:", size=FOOTNOTE_SIZE),
        Item(253, 720, "Footnote verse.", "tiit", FOOTNOTE_SIZE),
    ], separator_y=690)])
    runs = EdgeCaseSurvey.find_poem_runs(doc[0], 1, CFG)
    assert [(r.region, r.lines) for r in runs] == [
        ("body", ["Line one,", "Line two."]),
        ("footnote", ["Footnote verse."]),
    ]


def test_real_page_307_dialogue_break(data_pdf):
    breaks = EdgeCaseSurvey.find_dialogue_breaks(data_pdf[306], 307, CFG)
    assert any(b.kind == "page_end" for b in breaks)


def test_real_page_102_poem(data_pdf):
    runs = EdgeCaseSurvey.find_poem_runs(data_pdf[101], 102, CFG)
    assert len(runs) == 1 and len(runs[0].lines) == 4 and runs[0].region == "body"
    assert "Italic" in " ".join(runs[0].fonts)


def test_real_footnote_chain_175_176(data_pdf):
    chains = EdgeCaseSurvey.find_footnote_chains(data_pdf, 170, 180, CFG)
    assert FootnoteChain(num=2, pages=[175, 176], snippet=chains[0].snippet) in chains


def test_real_story_41_recurring_footnote_run(data_pdf):
    runs = EdgeCaseSurvey.find_recurring_footnote_runs(data_pdf, 296, 311, CFG)
    run_1 = [r for r in runs if r.num == 1]
    assert run_1 and len(run_1[0].pages) >= 11


def test_catalog_lists_every_class(data_pdf):
    survey = EdgeCaseSurvey.survey_range(data_pdf, 300, 310, CFG, label="test")
    md = EdgeCaseSurvey.render_catalog([survey])
    for heading in ("Poem candidates", "Long-footnote spans", "Dialogue page-boundary breaks"):
        assert heading in md
    assert "307" in md


def test_cli_writes_catalog(tmp_path):
    out = tmp_path / "catalog.md"
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "survey_data.py"),
         "--pdf", os.path.join(ROOT, "data.pdf"), "--pages", "300-310", "--catalog", str(out)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "307" in out.read_text(encoding="utf-8")
