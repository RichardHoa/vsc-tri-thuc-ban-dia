# Technical Specification

## Project Overview

Extracts the Vietnamese folk-tale anthology *Kho Tàng Truyện Cổ Tích Việt-Nam* (`data.pdf`) into clean, per-story GitHub-flavored Markdown plus a `table_of_contents.json` index, then validates the extraction against the source PDF. Pure offline batch pipeline: read `data.pdf` (PyMuPDF), write `.md` + `.json` to an output directory. No server, no database, no network calls.

**Invariants (apply project-wide):**
- Vietnamese diacritics are never stripped, folded, or casefolded anywhere in the pipeline — text is compared/normalized only via `unicodedata.normalize("NFC", ...)`.
- `extractor/` modules are read/transform only; nothing under `extractor/` ever mutates `data.pdf`.
- `validate_extraction.py` is a reporting tool, not a CI gate — it always exits 0 and never raises past its `main()`.
- Coordinate-based geometry filtering (headers/footers/footnotes) always prefers a page's drawn separator line (`find_footer_separator_y`) over the flat-`y` fallback constants in `ExtractorConfig`; the fallback exists only for pages with no drawn rule.

## Core Modules (`extractor/`)

| Module | Responsibility |
|---|---|
| `models.py` | Dataclasses: `Verse`, `Footnote`, `StoryDefinition`, `StoryContent`, `ExtractorConfig` (all extraction thresholds/parameters). A story paragraph (`Paragraph`) is either a prose `str` or a `Verse` block; a `Footnote` carries flat `text` plus, only when it contains verse, `parts` (prose/`Verse` split), and `continued` for the head of a footnote carried over from the previous page. |
| `normalizer.py` | `TextNormalizer` — legacy-encoding repair, whitespace/punctuation cleanup, dialogue-line splitting, sentence-end detection. |
| `verse.py` | `VerseDetector` — marks PDF lines as verse from span fonts + geometry: non-bold italic (≥80% of letters) and indented past `verse_min_x0` (130), or a run of ≥2 short italic lines at the margin. All-caps headings, numbered footnote/list lines and fully parenthesized notes such as `(Tiếp theo)` are never verse. |
| `geometry.py` | `PdfGeometryHelper` — y-coordinate classification of header/footer/footnote/body regions and scene dividers, per page. |
| `toc.py` | `TableOfContentsParser` — parses the printed MỤC LỤC to resolve each Roman-numeral section's PDF page range (`SectionRange`), independent of story discovery. |
| `discovery.py` | `StoryDiscoveryEngine` — scans page blocks for Roman category headers and `N. TITLE` story headers, computing each story's page-range boundary from the next story's start. |
| `footnotes.py` | `FootnoteEngine` — parses footer-region text per page into individual numbered footnote entries (handles sequential multi-footnote blocks). Entries stay split per page, each with its own page. The unnumbered head of a page's footnote area continues the footnote left open on the previous page and inherits its number. Verse lines inside a footnote become `Footnote.parts`. |
| `engine.py` | `StoryExtractionEngine` — walks a story's page range, filters header/footer lines out via `geometry.py`, assembles paragraphs/dialogue/verse/KHẢO DỊ, inlines `[^N]` footnote markers. A dialogue item left open at a block end (a bare `-` anywhere, or unterminated text at the foot of a page) is held across the page loop and prepended to the next text. Verse runs are emitted in place as `Verse` blocks, merged across a page break. |
| `formatters.py` | `MarkdownRenderer` (StoryContent → `.md`; a `Verse` renders as a blockquote, one `> ` line per verse line, in the flow of the text; a footnote with verse continues as 4-space-indented blocks under its `[^N]:` line) and `TableOfContentsBuilder` (section map → `table_of_contents.json` dict). |
| `pipeline.py` | `FolkStoryPipeline` — orchestrates discovery → per-story extraction → render → write, for one `ExtractorConfig`. |
| `survey.py` | `EdgeCaseSurvey` — read-only scan of a page range for poem runs, footnotes continued over a page break (`find_footnote_chains`, also used by the validator), recurring per-page footnote numbers, and dialogue dashes left open at a block/page end, plus per-range layout stats; `render_catalog` writes the Markdown catalog. |
| `validation.py` | `ExtractionValidator` / `ValidationReporter` — read-only accuracy checks over already-extracted output. → see "Validation & Scoring" below. |

## Data Flow

1. **Extraction** (`extract_folk_stories.py` → `FolkStoryPipeline.run`): open `data.pdf` → `StoryDiscoveryEngine.discover_stories` finds story boundaries in a page range (or a MỤC LỤC-resolved section via `--section`) → per story, `StoryExtractionEngine.extract_single_story` (which internally calls `FootnoteEngine.collect_story_footnotes`) produces a `StoryContent` → `MarkdownRenderer.render` writes `story_NNN.md` → `TableOfContentsBuilder.build` writes `table_of_contents.json`.
2. **Section mode** (`--section`): `TableOfContentsParser.parse_sections` reads the MỤC LỤC once to get every Roman section's page range + `hard_stops` (pages where non-story material starts, e.g. volume front matter); each selected section runs through its own `FolkStoryPipeline` into `<output-dir>/<ROMAN>_<SLUG>/`.
3. **Validation** (`validate_extraction.py` → `ExtractionValidator.validate_section`): reads `table_of_contents.json` + each `story_NNN.md` back from an output directory, re-extracts the same page range's raw PyMuPDF text as ground truth, and scores/flags each story. Writes `validation_report.md` next to the input by default. Never touches extraction logic.

## Validation & Scoring

Two independent signal types, both computed per story in `ExtractionValidator.validate_section` (`extractor/validation.py`):

**Structural checks** (`check_structure`, `check_footnote_chains`, `check_completeness`) — empty title/category/body, orphan footnote markers vs. orphan footnote entries, `BARE_DASH_PARAGRAPH` (a paragraph that is only a dialogue dash), `FOOTNOTE_GAP:N` (a footnote number's pages leave the story range or go backwards, or a footnote continued over a page break in the raw PDF footer is missing its `[^N]` entry on a continuation page), `LOW_DENSITY` (chars/page below `MIN_CHARS_PER_PAGE = 800`), section-level story-count drift against the printed MỤC LỤC. A duplicate footnote number across *different* pages is a `notes` entry (expected — footnotes renumber per page), not a flag; duplicate on the *same* page is also just a note.

**Known source errata** — `KNOWN_SOURCE_ERRATA` (`extractor/validation.py`) allow-lists `(story_number, flag)` pairs caused by errors printed in the textbook itself. A listed flag moves to `source_errata`, and the story gets status `ERRATUM` (reported in its own section, not counted as needing review). Current entry: story 52 `ORPHAN_MARKER:3`.

**Text alignment** — `rendered_coverage` (fraction of rendered Markdown prose found in the raw PDF page text) is the sole sort key and threshold metric (`DEFAULT_THRESHOLD = 0.90`, status `REVIEW` below it or on any structural flag). It is scored **per segment**, not as one whole-document diff:
- The body prose (`split_rendered_segments`) is diffed against the story's full page-range raw text.
- Each footnote body is diffed against a window anchored to its own `(Trang P)` page (falling back to the full range when `P` is missing or outside the story).
- Segment results are combined length-weighted (`score_segments`).

Before diffing, the verse `> ` marker is stripped (text kept), and a footnote's indented continuation lines are attached to that footnote.

This split exists because `MarkdownRenderer` relocates every footnote to an end-of-file `### Chú thích` block while the raw PDF keeps them interleaved per page; a whole-blob diff is defeated by that reordering and produces false-low scores on footnote-heavy stories. On the current corpus (sections I–III, 2026-09-25) `rendered_coverage` scores exactly `1.000` on every story — it has no headroom below 1.000 on clean output, but sensitivity testing confirmed it still degrades correctly under injected contamination (see `process/general-plans/backlog/rendered-coverage-threshold-review_23-09-26.md`).

`raw_coverage` is **informational only** and must never be used to fail or sort a story — adjacent stories share PDF boundary pages, so a story's page range legitimately contains a neighbour's text, making raw coverage inherently noisy.

Memory bound: exactly one story's raw + rendered text is held at a time (`del` after each story) — never a whole-section blob, since `difflib.SequenceMatcher` is quadratic-ish.

## CLI Contracts

**`extract_folk_stories.py`** — `--pdf` (default `data.pdf`), `--start-page`/`--end-page` (default 86/200, ignored when `--section` given), `--output-dir` (default `extracted_stories`), `--story N` (single story only), `--section SPEC` (1-based MỤC LỤC index/range/list, e.g. `1`, `1-3`, `1,4`; resolves page ranges + `hard_stops` from the TOC and writes to `<output-dir>/<ROMAN>_<SLUG>/`), `--list-sections` (print and exit), `-v`. Non-zero exit only on an unhandled top-level exception.

**`survey_data.py`** — `--pdf`, `--section SPEC` (default `1-10`), `--pages A-B` (explicit range instead of `--section`), `--catalog` (default `.scratch/folk-story-pipeline-fixes/edge-case-catalog.md`). Read-only, and writes only the catalog. Non-zero exit only on an unhandled top-level exception.

**`validate_extraction.py`** — `--pdf`, `--section SPEC` (resolves `<output-dir>/<ROMAN>_<SLUG>/` as the input dir), `--output-dir`, `--input-dir` (explicit override), `--threshold` (default 0.90), `--report` (default `<input-dir>/validation_report.md`), `--extract-first` (opt-in: run extraction before validating), `-v`. Always exits 0 — failures are printed/reported, never raised past `main()`.
