# Progress

## Project Status

Core extraction + validation pipeline complete and stable. Dialogue dashes carry across page breaks, and verse renders as blockquotes (body and footnotes). Footnotes continued over a page break are merged into one `(Trang P-Q)` entry. Sections I–IV (93 stories) are extracted and validate clean: `rendered_coverage` 1.000 everywhere, story 52 a known textbook erratum. Sections V–X are not extracted yet. pytest suite in `tests/`.

## Completed

| Phase | Description | Date |
|-------|-------------|------|
| Core pipeline | Discovery, extraction, Markdown/TOC rendering (`extractor/{discovery,engine,footnotes,formatters,pipeline}.py`) | 2026-09 (pre-session) |
| Extraction accuracy validator | `extractor/validation.py` + `validate_extraction.py`: structural checks + `difflib`-based `rendered_coverage` scoring | 2026-09-23 |
| Edge-case survey | `extractor/survey.py` + `survey_data.py`: catalog of poem runs, multi-page footnotes, recurring footnote numbers, dialogue page-boundary breaks across sections I–X | 2026-09-25 |
| Dialogue / verse / footnote-continuation fixes | `engine.py` pending-dialogue carry across pages; `verse.py` + `Verse` blockquote rendering; `footnotes.py` continuation numbering | 2026-09-25 |
| Validator extension | `BARE_DASH_PARAGRAPH`, `FOOTNOTE_GAP:N`, blockquote-aware diffing | 2026-09-25 |
| Textbook-quirk handling | `(Tiếp theo)` skip, glued footnote numbers (`2Theo`), `errata.py` page fixes, `KNOWN_SOURCE_ERRATA` allow-list, merged `(Trang P-Q)` footnote continuations | 2026-09-25 |
| Test suite | pytest foundation (`tests/`, synthetic PDFs + real-PDF pins) | 2026-09-25 |
| Footnote-boundary & segment-aware coverage fix | `body_max_y` (geometry.py/engine.py) fixes footnote superscripts misread as body text near a drawn footer separator; `split_rendered_segments`/`score_matched`/`score_segments` (validation.py) fix false-low `rendered_coverage` on footnote-heavy stories caused by footnote relocation | 2026-09-23 |

## Known Issues / Blockers

None blocking. Textbook errors are handled explicitly: story 52 (`ORPHAN_MARKER:3`, allow-listed in `KNOWN_SOURCE_ERRATA`) and story 91 (page-560 marker repaired in `extractor/errata.py`).

## Next Steps

1. Extract and validate sections V–X one at a time (`extract_folk_stories.py --section N` → `validate_extraction.py --section N`, stopping on any `REVIEW`).
2. `rendered-coverage-threshold-review` (backlog, low priority) — reconsider raising `DEFAULT_THRESHOLD` from 0.90 now that clean output saturates at 1.000; sensitivity testing (contamination → score) already recorded. See `process/general-plans/backlog/rendered-coverage-threshold-review_23-09-26.md`.

## Deferred Work

- Optional remote-LLM judge pass over `REVIEW`-flagged stories (noted as out-of-scope future extension in `extractor/validation.py` module docstring) — not implemented, no current plan to implement.
