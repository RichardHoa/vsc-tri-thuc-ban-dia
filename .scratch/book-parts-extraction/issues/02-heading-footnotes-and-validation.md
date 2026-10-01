# 02: Heading footnotes, and a validation report over all three Parts

**What to build:** A footnote marker printed in any heading (Part, Section, Story or Essay title) renders as `[^N]` at its printed position instead of being stripped, while manifest titles stay clean. Today the marker is dropped and its definition is left orphaned in `### Chú thích`, which affects Stories 13, 21, 25, 47, 55 and 57 (mid-title in 25, 47 and 57). The validator's orphan-marker and orphan-footnote checks match on (page, number) rather than number alone, because footnote numbers restart per page and a same-numbered marker elsewhere currently hides the missing one. The validator also handles Essays and Introductions with the same structural checks and per-segment rendered coverage as Stories. MỤC LỤC's omission of Part 3 Section V's Essay 1 is recorded as a known source erratum rather than a review flag. One run over all three Parts produces a single report listing every flagged Story, Essay and Introduction. The report is report-only: each genuine defect it surfaces becomes its own follow-up ticket, and none are fixed here. Full context: `.scratch/book-parts-extraction/spec.md` (Heading footnotes, Validation). Glossary: `CONTEXT.md`.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Stories 13, 21, 25, 47, 55 and 57 render the heading marker at its printed position (e.g. `## 57. KIỆN NGÀNH[^1] ĐA`), and their manifest titles have no marker. Any Essay, Section or Part heading carrying a footnote does the same.
- [ ] The page-aware orphan check flags all 6 Stories on output from before the fix and none after, with no new orphan flags elsewhere in Part 2.
- [ ] A no-argument validation run covers all three Parts and writes one report, grouped Part → Section, listing every non-OK leaf with its flags. `--part` / `--section` narrow it.
- [ ] All 201 Stories still score rendered coverage 1.000. The 3 existing Story errata stay `ERRATUM`, and Part 3 Section V's count drift appears as a MỤC LỤC erratum, not a review flag.
- [ ] Tests cover the trailing (Story 13) and mid-title (Story 25) heading cases and the page-aware orphan check.
- [ ] The report has been reviewed, and each genuine defect it surfaces has a follow-up ticket under `.scratch/book-parts-extraction/issues/`.

## Comments
