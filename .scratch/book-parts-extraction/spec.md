# Book Parts extraction: Part 1 & Part 3 Essays, Part grouping, heading footnotes

Glossary: `CONTEXT.md` (Part, Section, Story, Essay, Introduction, Volume, MỤC LỤC).

## Problem Statement

The pipeline only extracts Part 2 (the 201 Stories) into a flat `extracted_stories/<ROMAN>_<SLUG>/` layout. The book's scholarly Parts — Part 1 (*Nghiên cứu truyện cổ tích nói chung và truyện cổ tích Việt-Nam*, PDF pp. 42–84) and Part 3 (*Nhận định tổng quát về kho tàng truyện cổ tích Việt-Nam*, pp. 1339–1433) — are not extracted at all, and the output doesn't reflect the MỤC LỤC hierarchy (Part → Section → Story/Essay). Roman-numeral Section ids collide across Parts (Part 3 continues Part 1's numbering: IV, V), so a flat layout can't hold them.

Separately, a footnote attached to a Story title is dropped: `StoryDiscoveryEngine.clean_story_title` (`extractor/discovery.py:49-52`) strips the marker digits, so the footnote definition lands in `### Chú thích` with no `[^N]` in the text. The validator misses this because its orphan check (`extractor/validation.py:~430`) compares footnote numbers only, and footnote numbers restart per page — a `[^1]` elsewhere in the story masks the missing title `[^1]`. Affected in Part 2: Stories 13, 21, 25, 47, 55, 57 (marker mid-title in 25, 47, 57).

## Solution

### Output layout

```
extracted_stories/
├── table_of_contents.json            # root: full Part → Section → leaf tree
├── validation_report.md              # one report over all three Parts
├── PHAN_THU_NHAT/
│   ├── I_BAN_CHAT_TRUYEN_CO_TICH/    { table_of_contents.json, essay_01.md … }
│   ├── II_LAI_LICH_TRUYEN_CO_TICH/
│   └── III_TRUYEN_CO_VIET_NAM_QUA_CAC_THOI_DAI/
├── PHAN_THU_HAI/
│   ├── introduction.md               # editorial preface, p. 85
│   ├── I_NGUON_GOC_SU_VAT/           { table_of_contents.json, story_NNN.md … }
│   └── … X_TRUYEN_VUI_TUOI_DI_DOM/
└── PHAN_THU_BA/
    ├── introduction.md               # pp. 1339–1341, before Section IV
    ├── IV_DAC_DIEM_CUA_TRUYEN_CO_TICH_VIET_NAM/
    └── V_THU_TIM_NGUON_GOC_TRUYEN_CO_TICH_VIET_NAM/
```

The 10 old flat `extracted_stories/<ROMAN>_<SLUG>/` folders are removed (replaced by `PHAN_THU_HAI/…`). No Volume level: Part 2 is one Part across Tập I–V.

### Scope boundaries

- Part page ranges come from MỤC LỤC (Part heading → next Part heading / LỜI SAU SÁCH), not hard-coded. Part 1 = 42–84, Part 2 = 85–1338, Part 3 = 1339–1433.
- Out of scope: front matter (pp. 20–41), back matter (LỜI SAU SÁCH p. 1434 onward: bibliography, reviews, memoir, index), and the `digitizing-vietnam-website` loader (it reads its own copy under `public/data/` and will be updated separately).
- MỤC LỤC is the guide, the printed text is the authority: Part 3 Section V's Essay 1 (*1. CÁC TRƯỜNG PHÁI CỔ TÍCH HỌC XƯA NAY VỚI VẤN ĐỀ CÁI "CHUNG" VÀ CÁI "RIÊNG"…*, p. 1392, set non-bold) is missing from MỤC LỤC but is extracted as a normal Essay.

### Essays

- An Essay heading is an all-caps `N. TITLE` line inside a Part 1/Part 3 Section. Mixed-case numbered prose lists inside an Essay (e.g. `1. Yếu tố tưởng tượng…`, p. 1392) are body text, not headings. Essay numbering restarts per Section.
- Essays reuse the existing body machinery: geometry filtering, paragraphs, verse, footnotes (incl. continued-over-page-break merging), errata.
- Essay Section manifest: same shape as Story Section manifests, with `essays: [{essay_number, title, start_page, end_page, markdown_file, footnote_count}]`.

### Introductions

Unnumbered prose that opens a Part before its first Section, rendered to `<PART>/introduction.md` with its own footnotes. Part 2's preface contains a numbered editorial list (`1. Trong phần kho tàng…`) that must not be discovered as Stories.

### Root manifest

`extracted_stories/table_of_contents.json` describes the whole tree: each Part (id, title, page range, introduction file if any) → Sections (id, title, folder) → leaves (Story or Essay entries as in the Section manifests).

### Heading footnotes

A footnote marker printed in a heading — Part, Section, Story or Essay title — renders as `[^N]` at its printed position (`## 25. GỐC TÍCH RUỘNG THÁC ĐAO[^1] HAY LÀ TRUYỆN LÊ PHỤNG HIỂU`). Manifest `title` fields stay clean (no marker).

### CLI

All three scripts (`extract_folk_stories.py`, `survey_data.py`, `validate_extraction.py`) share the same selection rules:
- `--part N` (1–3) selects a Part; `--section SPEC` selects Sections within that Part (1-based MỤC LỤC index/range/list).
- `--section` without `--part` is an error.
- No selection = all three Parts.
- No backward compatibility with the old Part-2-only `--section` meaning, and the old `--start-page`/`--end-page` 86–200 default goes away.

### Validation

- The validator handles Essays and Introductions with the same structural checks and per-segment `rendered_coverage` as Stories.
- Orphan marker / orphan footnote checks match on **(page, number)**, not number alone.
- Section-level count drift for Part 3 Section V (4 Essays found vs 3 in MỤC LỤC) is a known MỤC LỤC erratum, not a review flag.
- Run once over all three Parts into a single `extracted_stories/validation_report.md` listing every flagged Story/Essay/Introduction. **Report only** — defects found become follow-up issues; this work fixes none of them (except heading footnotes, which it fixes explicitly).

## Testing Decisions

- pytest, following `tests/` conventions.
- Heading footnotes: Stories 13, 21, 25, 47, 55, 57 render the marker in the heading at the printed position. The page-aware orphan check flags all 6 on the pre-fix output and none after.
- Discovery: Part 1 yields Sections I–III with 6/5/4 Essays. Part 3 yields IV (4 Essays) and V (4 Essays, incl. V.1). Mixed-case numbered lists aren't Essays. Part 2's preface list isn't Stories, and Part 2 still yields 201 Stories across I–X.
- CLI: `--section` without `--part` exits non-zero with a clear message. `--part 3 --section 2` selects Part 3 Section V.
- All 201 Stories still score `rendered_coverage` 1.000 after the move.

## Out of Scope

Website loader / reader changes, displaying Essays on the website, front/back matter, fixing defects surfaced by the validation report.
