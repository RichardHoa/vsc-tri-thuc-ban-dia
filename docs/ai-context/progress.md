# Progress

## Project Status

The whole book is extracted to `extracted_stories/` as Part → Section → leaf: Part 1 (Sections I–III, 15 Essays), Part 2 (Introduction + Sections I–X, 201 Stories) and Part 3 (Introduction + Sections IV–V, 8 Essays), with per-Section and root manifests, plus the Bibliography (Sections I–III, 616 entries). One validation run over all three Parts covers 226 leaves, and rendered coverage is 1.000 on all of them. 5 Essays are flagged `REVIEW` for footnote defects (tickets 03–08 in `.scratch/book-parts-extraction/issues/`). Three Stories carry known textbook errata (status `ERRATUM`): 52, 97 and 108. Footnote markers printed in Story and Section headings render in place. pytest suite in `tests/` (174 tests).

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
| Book Parts extraction | All three Parts in the Part → Section → leaf layout, Essays and Introductions, `--part`/`--section` CLI (ticket 01) | 2026-10-01 |
| Heading footnotes & whole-book validation | Heading markers rendered in place; page-aware orphan checks; Essays/Introductions validated; parallel single-report run (ticket 02) | 2026-10-01 |
| Footnote-boundary & segment-aware coverage fix | `body_max_y` (geometry.py/engine.py) fixes footnote superscripts misread as body text near a drawn footer separator; `split_rendered_segments`/`score_matched`/`score_segments` (validation.py) fix false-low `rendered_coverage` on footnote-heavy stories caused by footnote relocation | 2026-09-23 |

## Known Issues / Blockers

None blocking. Textbook errors are handled explicitly. `KNOWN_SOURCE_ERRATA` allow-lists story 52 (`ORPHAN_MARKER:3@357`), 97 (`EMPTY_FOOTNOTE:1`, page 601) and 108 (`ORPHAN_MARKER:2@657`), and `KNOWN_TOC_ERRATA` allow-lists Part 3 Section V's count drift (MỤC LỤC omits Essay V.1). `extractor/errata.py` repairs story 91's full-size footnote marker (page 560). Essay footnote defects open in tickets 03–08: pages 44, 1373, 1399, 1406, 1423–1424 and 1397.

## Next Steps

1. `.scratch/book-parts-extraction/issues/03`–`08` — Essay footnote defects surfaced by the validation report.
2. `rendered-coverage-threshold-review` (backlog, low priority) — reconsider raising `DEFAULT_THRESHOLD` from 0.90 now that clean output saturates at 1.000.

## Deferred Work

- Optional remote-LLM judge pass over `REVIEW`-flagged stories (noted as out-of-scope future extension in `extractor/validation.py` module docstring) — not implemented, no current plan to implement.
