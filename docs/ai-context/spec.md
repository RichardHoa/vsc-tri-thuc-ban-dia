# Technical Specification

## Project Overview

Extracts the book *Kho Tàng Truyện Cổ Tích Việt-Nam* (`data.pdf`) into clean GitHub-flavored Markdown mirroring its MỤC LỤC hierarchy — Part → Section → Story (Part 2) or Essay (Parts 1, 3), plus each Part's Introduction — with per-Section and root `table_of_contents.json` manifests, then validates the extraction against the source PDF. Glossary: `CONTEXT.md`. Pure offline batch pipeline: read `data.pdf` (PyMuPDF), write `.md` + `.json` to an output directory. No server, no database, no network calls.

**Invariants (apply project-wide):**
- Vietnamese diacritics are never stripped, folded, or casefolded anywhere in the pipeline — text is compared/normalized only via `unicodedata.normalize("NFC", ...)`.
- `extractor/` modules are read/transform only; nothing under `extractor/` ever mutates `data.pdf`.
- `validate_extraction.py` is a reporting tool, not a CI gate — it exits 0 whatever it finds and never raises past its `main()`; only an argparse usage error exits non-zero.
- Section numbering is per Part (Roman numerals repeat: Part 3 continues Part 1's IV, V, colliding with Part 2's). Every script selects work with `--part N` + `--section SPEC` (1-based index within that Part); `--section` without `--part` is a usage error; no selection = all three Parts.
- Coordinate-based geometry filtering (headers/footers/footnotes) always prefers a page's drawn separator line (`find_footer_separator_y`) over the flat-`y` fallback constants in `ExtractorConfig`; the fallback exists only for pages with no drawn rule.

## Core Modules (`extractor/`)

| Module | Responsibility |
|---|---|
| `models.py` | Dataclasses: `Verse`, `Footnote`, `StoryDefinition`, `StoryContent`, `ExtractorConfig` (all extraction thresholds/parameters). `StoryDefinition`/`StoryContent` carry every leaf kind: a Story, an Essay (`category` = its Section) or an Introduction (`story_number` 0, no `title`, `category` = its Part). A leaf bounded mid-page sets `body_top` (body lines on `start_page` above it are skipped) and `body_bottom` (body lines on `end_page` at/below it are skipped); Stories own whole pages and leave both `None`. A story paragraph (`Paragraph`) is either a prose `str` or a `Verse` block; a `Footnote` carries flat `text` plus, only when it contains verse, `parts` (prose/`Verse` split), `end_page` (last page of a footnote merged across a page break), and `continued` for a continuation whose footnote starts before the story's range. |
| `normalizer.py` | `TextNormalizer` — legacy-encoding repair, whitespace/punctuation cleanup, dialogue-line splitting, sentence-end detection. |
| `verse.py` | `VerseDetector` — marks PDF lines as verse from span fonts + geometry: non-bold italic (≥80% of letters) and indented past `verse_min_x0` (130), or a run of ≥2 short italic lines at the margin. All-caps headings, numbered footnote/list lines and fully parenthesized notes such as `(Tiếp theo)` are never verse. |
| `errata.py` | `PAGE_TEXT_FIXES` / `apply_page_text_fixes` — page-scoped literal repairs of errors printed in data.pdf, applied to body lines by the engine (page 560: story 91's footnote marker is typeset full-size, `đười ươi1.` → `đười ươi[^1].`). |
| `geometry.py` | `PdfGeometryHelper` — y-coordinate classification of header/footer/footnote/body regions and scene dividers, per page. |
| `toc.py` | `TableOfContentsParser.parse_parts` — parses the printed MỤC LỤC into three `PartRange`s (heading → page before the next Part heading, or LỜI SAU SÁCH for Part 3; a Volume repeat of the current Part's heading doesn't open a new Part: Part 1 = 42–84, Part 2 = 85–1338, Part 3 = 1339–1433), each holding its Roman `SectionRange`s (page range + `hard_stops`, `path` = `<PART>/<ROMAN>_<SLUG>`). `select_parts` applies the CLI selection rules. Independent of leaf discovery. |
| `discovery.py` | `StoryDiscoveryEngine` — scans page blocks for Roman category headers and `N. TITLE` story headers, computing each story's page-range boundary from the next story's start. `PartLayoutDiscovery` — scans a Part's body lines for its title, Section headings and (Parts 1, 3) Essay headings, and bounds each Introduction/Essay from below its heading to the top of the next heading. An Essay heading is an all-caps (≥90% upper-case letters) `N. TITLE` line, wrapped over following all-caps lines; mixed-case numbered lines are prose. Headings are found in the printed text, not MỤC LỤC (Part 3 V.1 is printed but absent from MỤC LỤC). For Part 2 it stops at Section I, so only the Introduction is bounded. |
| `footnotes.py` | `FootnoteEngine` — parses footer-region text per page into individual numbered footnote entries (handles sequential multi-footnote blocks). A footnote number may be glued to its text (`2Theo`) or printed doubled (`33` for 3), and an empty footnote doesn't swallow the next number. A number inside a parenthesis that closes after it (`(1. …; 2. …)`) is part of the note, not a new footnote. The unnumbered head of a page's footnote area continues the footnote left open on the previous page and is merged into it: one entry covering `page`–`end_page`, rendered `(Trang P-Q)`. Only when that footnote starts before the story's range is the continuation kept as its own `continued` entry. Verse lines inside a footnote become `Footnote.parts`. |
| `engine.py` | `StoryExtractionEngine` — walks a story's page range, filters header/footer lines out via `geometry.py`, assembles paragraphs/dialogue/verse/KHẢO DỊ, inlines `[^N]` footnote markers. A dialogue item left open at a block end (a bare `-` anywhere, or unterminated text at the foot of a page) is held across the page loop and prepended to the next text. A superscript-size run holding a footnote number becomes `[^N]`. Punctuation typeset in the same run (`1. `) is kept after the marker. Verse runs are emitted in place as `Verse` blocks, merged across a page break. The `(Tiếp theo)` marker under a repeated section heading is skipped. For a leaf bounded mid-page, a footnote on the shared first/last page whose `(page, number)` marker lies only outside the bounds belongs to the neighbour and is dropped; one matched by no marker is kept. |
| `formatters.py` | `MarkdownRenderer` (StoryContent → `.md`; a `Verse` renders as a blockquote, one `> ` line per verse line, in the flow of the text; a footnote with verse continues as 4-space-indented blocks under its `[^N]:` line) and `TableOfContentsBuilder` (section map → Section manifest; `leaf_key` `stories` or `essays` names `total_<leaf_key>` and `sections[].<leaf_key>`). |
| `pipeline.py` | `FolkStoryPipeline` — Story discovery → per-story extraction → render → write, for one `ExtractorConfig` (one Part 2 Section). `BookPipeline` — the whole book or a selection: per Part, its Introduction (when the whole Part is selected), then each Section via `FolkStoryPipeline` (Stories) or `PartLayoutDiscovery` + extraction (Essays); finally rewrites the root manifest. |
| `cli.py` | `add_selection_args` / `check_selection_args` — the shared `--part`/`--section` arguments and the `--section`-requires-`--part` usage error. |
| `survey.py` | `EdgeCaseSurvey` — read-only scan of a page range for poem runs, footnotes continued over a page break (`find_footnote_chains`, also used by the validator), recurring per-page footnote numbers, and dialogue dashes left open at a block/page end, plus per-range layout stats; `render_catalog` writes the Markdown catalog. |
| `validation.py` | `ExtractionValidator` / `ValidationReporter` — read-only accuracy checks over already-extracted output. → see "Validation & Scoring" below. |

## Data Flow

1. **Extraction** (`extract_folk_stories.py` → `BookPipeline.run`): open `data.pdf` → `TableOfContentsParser.parse_parts` resolves Parts/Sections from MỤC LỤC → `select_parts` applies `--part`/`--section` → per Part: `PartLayoutDiscovery.discover` bounds the Introduction (and Essays in Parts 1, 3) → per Section: Stories through `FolkStoryPipeline` (`StoryDiscoveryEngine.discover_stories` within the Section's range, clamped by its `hard_stops`), Essays through `StoryExtractionEngine.extract_single_story` → `MarkdownRenderer.render` → manifests.
2. **Output layout**:
   ```
   <output-dir>/table_of_contents.json         root: {book_title, parts: [{part_id, part_number, part_title, start_page, end_page, introduction, sections: [{section_id, section_title, folder, start_page, end_page, stories|essays: [...]}]}]}
   <output-dir>/PHAN_THU_NHAT|HAI|BA/introduction.md     Parts 2 and 3 only
   <output-dir>/<PART>/<ROMAN>_<SLUG>/          story_NNN.md | essay_NN.md + table_of_contents.json (Section manifest)
   ```
   Story entries: `{story_number, title, start_page, end_page, markdown_file, has_khao_di, footnote_count}`; Essay entries: `{essay_number, title, start_page, end_page, markdown_file, footnote_count}`. The root manifest reads leaves back from each Section manifest on disk, so a partial run still describes the whole tree (unextracted Sections have no leaves). An Essay renders as `# <Section>` / `## N. TITLE`; an Introduction as `# PHẦN THỨ … . <Part title>`.
3. **Validation** (`validate_extraction.py` → `ExtractionValidator.validate_section` per selected Part 2 Section, results combined into one report): reads a Section's `table_of_contents.json` + each `story_NNN.md` back, re-extracts the same page range's raw PyMuPDF text as ground truth, and scores/flags each story. Essay/Introduction Sections are skipped. Never touches extraction logic.

## Validation & Scoring

Two independent signal types, both computed per story in `ExtractionValidator.validate_section` (`extractor/validation.py`):

**Structural checks** (`check_structure`, `check_footnote_chains`, `check_completeness`) — empty title/category/body, orphan footnote markers vs. orphan footnote entries, `BARE_DASH_PARAGRAPH` (a paragraph that is only a dialogue dash), `EMPTY_FOOTNOTE:N` (a footnote definition with no text), `FOOTNOTE_GAP:N` (a footnote number's pages leave the story range or go backwards, or a footnote continued over a page break in the raw PDF footer has a page not covered by an `[^N]` entry's `(Trang P)` / `(Trang P-Q)` range), `LOW_DENSITY` (chars/page below `MIN_CHARS_PER_PAGE = 800`), section-level story-count drift against the printed MỤC LỤC. A duplicate footnote number across *different* pages is a `notes` entry (expected — footnotes renumber per page), not a flag; duplicate on the *same* page is also just a note.

**Known source errata** — `KNOWN_SOURCE_ERRATA` (`extractor/validation.py`) allow-lists `(story_number, flag)` pairs caused by errors printed in the textbook itself. A listed flag moves to `source_errata`, and the story gets status `ERRATUM` (reported in its own section, not counted as needing review). Current entries: story 52 `ORPHAN_MARKER:3`, 97 `EMPTY_FOOTNOTE:1`, 108 `ORPHAN_MARKER:2`.

**Text alignment** — `rendered_coverage` (fraction of rendered Markdown prose found in the raw PDF page text) is the sole sort key and threshold metric (`DEFAULT_THRESHOLD = 0.90`, status `REVIEW` below it or on any structural flag). It is scored **per segment**, not as one whole-document diff:
- The body prose (`split_rendered_segments`) is diffed against the story's full page-range raw text.
- Each footnote body is diffed against a window anchored to its own `(Trang P)` page, or `P-Q` range for a merged footnote (falling back to the full range when `P` is missing or outside the story).
- Segment results are combined length-weighted (`score_segments`).

Before diffing, the verse `> ` marker is stripped (text kept), and a footnote's indented continuation lines are attached to that footnote.

This split exists because `MarkdownRenderer` relocates every footnote to an end-of-file `### Chú thích` block while the raw PDF keeps them interleaved per page; a whole-blob diff is defeated by that reordering and produces false-low scores on footnote-heavy stories. On the current corpus (sections I–X, 201 stories, 2026-09-25) `rendered_coverage` scores exactly `1.000` on every story — it has no headroom below 1.000 on clean output, but sensitivity testing confirmed it still degrades correctly under injected contamination (see `process/general-plans/backlog/rendered-coverage-threshold-review_23-09-26.md`).

`raw_coverage` is **informational only** and must never be used to fail or sort a story — adjacent stories share PDF boundary pages, so a story's page range legitimately contains a neighbour's text, making raw coverage inherently noisy.

Memory bound: exactly one story's raw + rendered text is held at a time (`del` after each story) — never a whole-section blob, since `difflib.SequenceMatcher` is quadratic-ish.

## CLI Contracts

All three scripts share `--part N` (1–3) / `--section SPEC` (1-based index/range/list within the Part, e.g. `1`, `1-3`, `1,4`); `--section` without `--part` exits 2 with `--section requires --part`; no selection = all three Parts.

**`extract_folk_stories.py`** — `--pdf` (default `data.pdf`), `--output-dir` (default `extracted_stories`), `--part`/`--section`, `--story N` (one Part 2 Story only; implies `--part 2`, error with another `--part`), `--list-sections` (print each Part with its Sections and page ranges, then exit), `-v`. Non-zero exit on a usage error or an unhandled top-level exception.

**`survey_data.py`** — `--pdf`, `--part`/`--section`, `--pages A-B` (explicit range instead of the selection), `--catalog` (default `.scratch/folk-story-pipeline-fixes/edge-case-catalog.md`). Essay Sections are surveyed without Story attribution. Read-only, and writes only the catalog. Non-zero exit on a usage error or an unhandled top-level exception.

**`validate_extraction.py`** — `--pdf`, `--part`/`--section` (resolves `<output-dir>/<PART>/<ROMAN>_<SLUG>/` for each selected Part 2 Section), `--output-dir`, `--input-dir` (explicit single Section dir override), `--threshold` (default 0.90), `--report` (default `<input-dir or output-dir>/validation_report.md`), `--extract-first` (opt-in: run `BookPipeline` for the selection first), `-v`. Exits 0 except on a usage error.
