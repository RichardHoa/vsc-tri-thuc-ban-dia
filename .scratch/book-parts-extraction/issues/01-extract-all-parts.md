# 01: Extract all three Parts into the Part → Section → leaf layout

**What to build:** Running the extractor with no selection produces the whole book's MỤC LỤC hierarchy on disk: Part 1 Essays (Sections I–III), Part 2 Stories (Sections I–X) and Part 3 Essays (Sections IV–V), each under its own Part folder, plus the Part 2 and Part 3 Introductions, per-Section manifests and a root manifest describing the full Part → Section → leaf tree. Part and Section page ranges are resolved from MỤC LỤC, ignoring the per-Volume repeats of the `PHẦN THỨ HAI` heading; Part 3 ends where LỜI SAU SÁCH begins. Part 3 Section V's Essay 1 is extracted even though MỤC LỤC omits it, because the printed text is the authority. An Essay heading is an all-caps numbered title, and mixed-case numbered prose lists inside an Essay or Introduction are body text. All three scripts select work with `--part N` plus `--section SPEC` within that Part. `--section` without `--part` is an error, and no selection means all three Parts. The old Part-2-only layout and CLI are replaced, not kept alongside. Full context: `.scratch/book-parts-extraction/spec.md` (Output layout, Scope boundaries, Essays, Introductions, Root manifest, CLI). Glossary: `CONTEXT.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human

- [x] A no-argument run writes `PHAN_THU_NHAT/`, `PHAN_THU_HAI/` and `PHAN_THU_BA/`, plus a root `table_of_contents.json` matching the spec's shape. The old flat Section folders are gone (left uncommitted for review).
- [x] Part 1: Sections I/II/III yield 6/5/4 Essays whose titles and start pages match MỤC LỤC.
- [x] Part 3: Section IV yields 4 Essays and Section V yields 4 (V.1–V.4), with V.1 starting on p. 1392. No Essay comes from a mixed-case numbered list.
- [x] Part 2 still yields exactly 201 Stories across I–X, with each Story's Markdown unchanged apart from its new location. Its preface's numbered editorial list is not discovered as Stories.
- [x] Part 2 and Part 3 Introductions are written to their Part folders with their own footnotes. Part 1 has none.
- [x] Essay and Introduction footnotes (including ones continued over a page break) and verse render the same way they do in Stories.
- [x] Listing Sections shows each Part with its Sections and page ranges, and Part 3's IV/V don't collide with Part 2's IV/V.
- [x] `--section` without `--part` exits non-zero with a clear message in all three scripts. `--part 3 --section 2` selects Part 3 Section V.
- [x] Tests cover Part/Section range resolution, Essay discovery boundaries, the Introductions and the CLI rules. The AI-context spec's CLI contracts and data flow are updated.

## Comments

- 2026-10-01 (agent): Implemented, uncommitted for review. 141 tests pass. A no-argument run's 201 Stories and Part 2 Section manifests are byte-identical to the pre-change `--section 1-10` output (`diff -r`). The full validator pass was skipped at the developer's request. Note for 02: p. 1397's footnote is printed `142.` and has no matching marker, so it's kept in both V.1 and V.2 (an unmatched footnote on a shared page is kept, never dropped). V.2 also has an unmatched `[^4]` definition.
