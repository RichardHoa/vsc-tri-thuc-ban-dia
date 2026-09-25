# Progress

## Project Status

Core extraction + validation pipeline complete and stable. Dialogue dashes carry across page breaks, verse renders as blockquotes (body and footnotes), and footnotes continued over a page break keep their number. Sections I–III (61 stories) are extracted with the current pipeline. `rendered_coverage` is 1.000 on every story. I–III validate clean (story 52 is a known textbook erratum). IV is extracted but has two `REVIEW` stories. V–X are not extracted yet. pytest suite in `tests/`.

## Completed

| Phase | Description | Date |
|-------|-------------|------|
| Core pipeline | Discovery, extraction, Markdown/TOC rendering (`extractor/{discovery,engine,footnotes,formatters,pipeline}.py`) | 2026-09 (pre-session) |
| Extraction accuracy validator | `extractor/validation.py` + `validate_extraction.py`: structural checks + `difflib`-based `rendered_coverage` scoring | 2026-09-23 |
| Edge-case survey | `extractor/survey.py` + `survey_data.py`: catalog of poem runs, multi-page footnotes, recurring footnote numbers, dialogue page-boundary breaks across sections I–X | 2026-09-25 |
| Dialogue / verse / footnote-continuation fixes | `engine.py` pending-dialogue carry across pages; `verse.py` + `Verse` blockquote rendering; `footnotes.py` continuation numbering | 2026-09-25 |
| Validator extension | `BARE_DASH_PARAGRAPH`, `FOOTNOTE_GAP:N`, blockquote-aware diffing | 2026-09-25 |
| Test suite | pytest foundation (`tests/`, synthetic PDFs + real-PDF pins) | 2026-09-25 |
| Footnote-boundary & segment-aware coverage fix | `body_max_y` (geometry.py/engine.py) fixes footnote superscripts misread as body text near a drawn footer separator; `split_rendered_segments`/`score_matched`/`score_segments` (validation.py) fix false-low `rendered_coverage` on footnote-heavy stories caused by footnote relocation | 2026-09-23 |

## Known Issues / Blockers

- **Section-by-section extraction is paused at IV.** Stories 86 (`ORPHAN_MARKER:3`: page 536 prints `2Theo` with no space after the footnote number) and 91 (`ORPHAN_FOOTNOTE:1`: page 560's footnote marker is typeset full-size, not superscript) are `REVIEW`. Waiting on a human decision (allow-list or fix; see `.scratch/folk-story-pipeline-fixes/spec.md` → Comments). Story 52's out-of-sequence footnote number is allow-listed in `KNOWN_SOURCE_ERRATA` (status `ERRATUM`).
- `(Tiếp theo)` (section-restart marker at volume boundaries, pages 296 and 1160) leaks into the first paragraph of stories 41 and 176. Not flagged by the validator.

## Next Steps

1. Resolve stories 86 and 91 (section IV), then extract and validate sections V–X one at a time (`extract_folk_stories.py --section N` → `validate_extraction.py --section N`, stopping on any `REVIEW`).
2. `rendered-coverage-threshold-review` (backlog, low priority) — reconsider raising `DEFAULT_THRESHOLD` from 0.90 now that clean output saturates at 1.000; sensitivity testing (contamination → score) already recorded. See `process/general-plans/backlog/rendered-coverage-threshold-review_23-09-26.md`.

## Deferred Work

- Optional remote-LLM judge pass over `REVIEW`-flagged stories (noted as out-of-scope future extension in `extractor/validation.py` module docstring) — not implemented, no current plan to implement.
