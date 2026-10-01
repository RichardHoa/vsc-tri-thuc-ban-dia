# Project Structure

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Runtime | Python 3 (`from __future__ import annotations` throughout) | No async, no web framework |
| PDF parsing | PyMuPDF (`fitz`), `>=1.24` (`requirements.txt`) | Only third-party dependency |
| Output | Markdown (`.md`) + JSON | No database |
| Tests | pytest (`requirements-dev.txt`, `pytest.ini`) | `tests/`: synthetic in-memory PDFs (base-14 fonts) per layout feature + pinned real `data.pdf` instances |

## File Tree

```
vsc-tri-thuc-ban-dia/
├── data.pdf                        # Source scanned/OCR'd PDF anthology (not extraction output)
├── extract_folk_stories.py         # CLI: discover/extract/render stories → Markdown + TOC json
├── validate_extraction.py          # CLI: validate already-extracted output against data.pdf
├── survey_data.py                  # CLI: edge-case survey of data.pdf → Markdown catalog
├── requirements.txt
├── requirements-dev.txt            # + pytest
├── pytest.ini
├── tests/                          # pytest suite (conftest.py builds synthetic PDFs)
├── extractor/                      # Library package — see spec.md "Core Modules"
│   ├── __init__.py                 # Public re-exports for the two CLI entrypoints
│   ├── models.py
│   ├── normalizer.py
│   ├── errata.py
│   ├── verse.py
│   ├── geometry.py
│   ├── toc.py
│   ├── discovery.py
│   ├── footnotes.py
│   ├── engine.py
│   ├── formatters.py
│   ├── pipeline.py
│   ├── cli.py
│   ├── survey.py
│   └── validation.py
├── extracted_stories/              # Extraction output (gitignored)
│   ├── table_of_contents.json      # Root manifest: Part → Section → leaf tree
│   ├── validation_report.md        # Written by validate_extraction.py (one report, all selected Parts)
│   ├── PHAN_THU_NHAT/              # Part 1: Sections I–III, essay_NN.md
│   ├── PHAN_THU_HAI/               # Part 2: introduction.md + Sections I–X
│   │   └── I_NGUON_GOC_SU_VAT/     # story_NNN.md + table_of_contents.json (Section manifest)
│   └── PHAN_THU_BA/                # Part 3: introduction.md + Sections IV–V, essay_NN.md
├── .scratch/                       # Per-effort working artifacts (plans, edge-case catalog) — not system docs
├── docs/
│   ├── ai-context/                 # This bundle: spec.md, project-structure.md, progress.md, deployment-infrastructure.md
│   ├── open-issues/, business/, design-brand/, legal/  # Empty (.gitkeep only)
├── process/                        # RIPER-5 planning kit (plans, context, seeds) — not application code
│   ├── context/                    # all-context.md, planning/, tests/ — living project-context notes
│   └── general-plans/              # active/ backlog/ completed/ — dated plan+report docs
├── AGENTS.md                       # Codex second-opinion consultant prompt (see CLAUDE.md §4 "second opinion")
├── GEMINI.md                       # Gemini second-opinion consultant prompt, same role as AGENTS.md
└── CLAUDE.md
```

## Directory Conventions

- **`extracted_stories/<PART>/<ROMAN>_<SLUG>/`**: one directory per Section, under its Part folder (`PHAN_THU_NHAT|HAI|BA`). `<SLUG>` is the section title ASCII-slugged (`SectionRange.folder_name` in `extractor/toc.py`). Each holds `story_NNN.md` or `essay_NN.md` plus the Section's `table_of_contents.json`.
- **`process/`**: RIPER-5 planning-kit output, not read by the extractor at runtime. Dated plan docs under `process/general-plans/{active,backlog,completed}/` record design decisions and follow-up work; `completed/` entries are historical (their shipped architecture, if any, is folded into `spec.md`).
