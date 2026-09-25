# Progress

## Project Status

Core extraction + validation pipeline complete and stable. Sections I–III of the anthology (61 stories total) are extracted; `rendered_coverage` scores 1.000 on every healthy story in the current corpus. No automated test suite yet.

## Completed

| Phase | Description | Date |
|-------|-------------|------|
| Core pipeline | Discovery, extraction, Markdown/TOC rendering (`extractor/{discovery,engine,footnotes,formatters,pipeline}.py`) | 2026-09 (pre-session) |
| Extraction accuracy validator | `extractor/validation.py` + `validate_extraction.py`: structural checks + `difflib`-based `rendered_coverage` scoring | 2026-09-23 |
| Footnote-boundary & segment-aware coverage fix | `body_max_y` (geometry.py/engine.py) fixes footnote superscripts misread as body text near a drawn footer separator; `split_rendered_segments`/`score_matched`/`score_segments` (validation.py) fix false-low `rendered_coverage` on footnote-heavy stories caused by footnote relocation | 2026-09-23 |

## Known Issues / Blockers

None currently blocking.

## Next Steps

1. `pytest-unit-tests-foundation` (backlog, low priority) — no test runner exists yet; `body_max_y`, `split_rendered_segments`, `score_matched` are the cheapest pure-function starting points (no PDF fixture needed). See `process/general-plans/backlog/pytest-unit-tests-foundation_23-09-26.md`.
2. `rendered-coverage-threshold-review` (backlog, low priority) — reconsider raising `DEFAULT_THRESHOLD` from 0.90 now that clean output saturates at 1.000; sensitivity testing (contamination → score) already recorded. See `process/general-plans/backlog/rendered-coverage-threshold-review_23-09-26.md`.

## Deferred Work

- Optional remote-LLM judge pass over `REVIEW`-flagged stories (noted as out-of-scope future extension in `extractor/validation.py` module docstring) — not implemented, no current plan to implement.
