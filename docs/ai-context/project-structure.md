# Project Structure

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Runtime | Python 3 (`from __future__ import annotations` throughout) | No async, no web framework |
| PDF parsing | PyMuPDF (`fitz`), `>=1.24` (`requirements.txt`) | Only third-party dependency |
| Output | Markdown (`.md`) + JSON | No database |
| Tests | none yet | see `docs/ai-context/progress.md` |

## File Tree

```
vsc-tri-thuc-ban-dia/
├── data.pdf                        # Source scanned/OCR'd PDF anthology (not extraction output)
├── extract_folk_stories.py         # CLI: discover/extract/render stories → Markdown + TOC json
├── validate_extraction.py          # CLI: validate already-extracted output against data.pdf
├── requirements.txt
├── extractor/                      # Library package — see spec.md "Core Modules"
│   ├── __init__.py                 # Public re-exports for the two CLI entrypoints
│   ├── models.py
│   ├── normalizer.py
│   ├── geometry.py
│   ├── toc.py
│   ├── discovery.py
│   ├── footnotes.py
│   ├── engine.py
│   ├── formatters.py
│   ├── pipeline.py
│   └── validation.py
├── extracted_stories/              # Extraction output, --section mode: <ROMAN>_<SLUG>/ per section
│   ├── II_SU_TICH_DAT_NUOC_VIET/
│   └── III_SU_TICH_CAC_CAU_VI/
│       ├── story_NNN.md            # One per extracted story
│       ├── table_of_contents.json
│       └── validation_report.md    # Written by validate_extraction.py
├── I_stories/                      # Extraction output for section I (flat --start-page/--end-page run)
│   ├── story_NNN.md
│   └── table_of_contents.json
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

- **`extracted_stories/<ROMAN>_<SLUG>/`**: one directory per Roman-numeral section, produced by `extract_folk_stories.py --section`. `<SLUG>` is the section title ASCII-slugged (`SectionRange.folder_name` in `extractor/toc.py`). Each holds `story_NNN.md` (one per story), `table_of_contents.json`, and — once validated — `validation_report.md`.
- **`I_stories/`**: an older/alternate output produced with `--start-page`/`--end-page` directly rather than `--section`, so it sits at repo root instead of under `extracted_stories/`. Same internal file shape as a section directory.
- **`process/`**: RIPER-5 planning-kit output, not read by the extractor at runtime. Dated plan docs under `process/general-plans/{active,backlog,completed}/` record design decisions and follow-up work; `completed/` entries are historical (their shipped architecture, if any, is folded into `spec.md`).
