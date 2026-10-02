# 02: Heading footnotes, and a validation report over all three Parts

**What to build:** A footnote marker printed in any heading (Part, Section, Story or Essay title) renders as `[^N]` at its printed position instead of being stripped, while manifest titles stay clean. Today the marker is dropped and its definition is left orphaned in `### Chú thích`, which affects Stories 13, 21, 25, 47, 55 and 57 (mid-title in 25, 47 and 57). The validator's orphan-marker and orphan-footnote checks match on (page, number) rather than number alone, because footnote numbers restart per page and a same-numbered marker elsewhere currently hides the missing one. The validator also handles Essays and Introductions with the same structural checks and per-segment rendered coverage as Stories. MỤC LỤC's omission of Part 3 Section V's Essay 1 is recorded as a known source erratum rather than a review flag. One run over all three Parts produces a single report listing every flagged Story, Essay and Introduction. The report is report-only: each genuine defect it surfaces becomes its own follow-up ticket, and none are fixed here. Full context: `.scratch/book-parts-extraction/spec.md` (Heading footnotes, Validation). Glossary: `CONTEXT.md`.

**Blocked by:** 01

**Status:** resolved

- [x] Stories 13, 21, 25, 47, 55 and 57 render the heading marker at its printed position (e.g. `## 57. KIỆN NGÀNH[^1] ĐA`), and their manifest titles have no marker. Any Essay, Section or Part heading carrying a footnote does the same.
- [x] The page-aware orphan check flags all 6 Stories on output from before the fix and none after, with no new orphan flags elsewhere in Part 2.
- [x] A no-argument validation run covers all three Parts and writes one report, grouped Part → Section, listing every non-OK leaf with its flags. `--part` / `--section` narrow it.
- [x] All 201 Stories still score rendered coverage 1.000. The 3 existing Story errata stay `ERRATUM`, and Part 3 Section V's count drift appears as a MỤC LỤC erratum, not a review flag.
- [x] Tests cover the trailing (Story 13) and mid-title (Story 25) heading cases and the page-aware orphan check.
- [x] The report has been reviewed, and each genuine defect it surfaces has a follow-up ticket under `.scratch/book-parts-extraction/issues/`.

## Comments

- 2026-10-01 (agent): Implemented, uncommitted for review. 174 tests pass.
  - **Heading markers:** Section headings carry markers too, not just Stories: III on p. 255 and its Tập II repeat on p. 296, and X on p. 1256. Each marker renders in the Story that heading opens (36, 41, 189). No Essay or Part heading in the book carries a marker. I checked every heading span, so `PartLayoutDiscovery` has no marker wiring.
  - **Re-extraction:** compared with the previous output, only these 9 heading lines changed. Stories 137–139 also moved from a bogus `C. HI` Section to `VII.`. That came from stale files on disk, not from this change.
  - **Page-aware check on pre-fix output:** flags exactly the 9 heading Stories (`ORPHAN_FOOTNOTE:1@<start page>`) and nothing else in Part 2. Errata keys now carry the page (`ORPHAN_MARKER:3@357`, `ORPHAN_MARKER:2@657`).
  - **Full no-argument run:** 226 leaves (201 Stories, 23 Essays, 2 Introductions), 11m46s on 8 workers (`--workers`, default CPU count). Rendered coverage is 1.000 on all of them. The 3 Story errata stay `ERRATUM`, and Part 3 V's drift is a MỤC LỤC erratum.
  - **Report:** 5 Essays flagged, all genuine. Follow-ups filed as 03–08.
- 2026-10-02 (developer, via agent): Resolved: finished.
