# Progress

## Project Status

The full anthology (PHẦN THỨ HAI, sections I–X, 201 stories) is extracted to `extracted_stories/<ROMAN>_<SLUG>/`, and every section validates with no `REVIEW` stories. `rendered_coverage` is 1.000 on all 201. Three stories carry known textbook errata (status `ERRATUM`): 52, 97 and 108. Dialogue dashes carry across page breaks, verse renders as blockquotes (body and footnotes), and footnotes continued over a page break are merged into one `(Trang P-Q)` entry. pytest suite in `tests/` (101 tests).

## Completed

| Phase | Description | Date |
|-------|-------------|------|
| Core pipeline | Discovery, extraction, Markdown/TOC rendering (`extractor/{discovery,engine,footnotes,formatters,pipeline}.py`) | 2026-09 (pre-session) |
| Extraction accuracy validator | `extractor/validation.py` + `validate_extraction.py`: structural checks + `difflib`-based `rendered_coverage` scoring | 2026-09-23 |
| Edge-case survey | `extractor/survey.py` + `survey_data.py`: catalog of poem runs, multi-page footnotes, recurring footnote numbers, dialogue page-boundary breaks across sections I–X | 2026-09-25 |
| Dialogue / verse / footnote-continuation fixes | `engine.py` pending-dialogue carry across pages; `verse.py` + `Verse` blockquote rendering; `footnotes.py` continuation numbering | 2026-09-25 |
| Validator extension | `BARE_DASH_PARAGRAPH`, `FOOTNOTE_GAP:N`, blockquote-aware diffing | 2026-09-25 |
| Textbook-quirk handling | `(Tiếp theo)` skip, glued footnote numbers (`2Theo`), `errata.py` page fixes, `KNOWN_SOURCE_ERRATA` allow-list, merged `(Trang P-Q)` footnote continuations | 2026-09-25 |
| Full I–X extraction | Sections I–X (201 stories) extracted and validated clean one at a time; doubled footnote numbers (`33`, `11`), empty footnotes (`EMPTY_FOOTNOTE:N`) and errata 97/108 handled along the way | 2026-09-25 |
| Test suite | pytest foundation (`tests/`, synthetic PDFs + real-PDF pins) | 2026-09-25 |
| Footnote-boundary & segment-aware coverage fix | `body_max_y` (geometry.py/engine.py) fixes footnote superscripts misread as body text near a drawn footer separator; `split_rendered_segments`/`score_matched`/`score_segments` (validation.py) fix false-low `rendered_coverage` on footnote-heavy stories caused by footnote relocation | 2026-09-23 |

## Known Issues / Blockers

None blocking. Textbook errors are handled explicitly. `KNOWN_SOURCE_ERRATA` allow-lists story 52 (`ORPHAN_MARKER:3`, page 357), 97 (`EMPTY_FOOTNOTE:1`, page 601) and 108 (`ORPHAN_MARKER:2`, page 657). `extractor/errata.py` repairs story 91's full-size footnote marker (page 560).

## Next Steps

1. `rendered-coverage-threshold-review` (backlog, low priority) — reconsider raising `DEFAULT_THRESHOLD` from 0.90 now that clean output saturates at 1.000.

## Deferred Work

- Optional remote-LLM judge pass over `REVIEW`-flagged stories (noted as out-of-scope future extension in `extractor/validation.py` module docstring) — not implemented, no current plan to implement.
