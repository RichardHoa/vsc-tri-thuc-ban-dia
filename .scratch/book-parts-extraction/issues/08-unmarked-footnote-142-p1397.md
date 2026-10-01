# 08: Unmarked footnote "142." on p. 1397 is duplicated in Essays V.1 and V.2

**What to build:** Page 1397 is shared by Part 3 Section V Essays 1 and 2. Its footer prints `142. Dẫn trong Pu-li-lốp (Poutilov). Phương pháp luận nghiên cứu lịch sử so sánh về phôn-clo (folklore).`, and no superscript marker on the page matches it. That is a printing error in the book. An unmatched footnote on a shared page is kept rather than dropped (ticket 01), so it renders as `[^142]` in both Essays, and both are flagged `ORPHAN_FOOTNOTE:142@1397`. Decide which Essay owns it from the printed text (the page's body: V.1's ending above the `2. NGUỒN GỐC NGOẠI LAI…` heading at y 576, or V.2's opening), render it only there, and allow-list the remaining flag in `KNOWN_SOURCE_ERRATA` (keys `"Essay V.1"` / `"Essay V.2"`) with the reason.

**Blocked by:** None

**Status:** needs-triage

- [ ] The footnote appears in exactly one Essay, and that Essay's report status is `ERRATUM` with the printed-number reason.
- [ ] The other Essay has no `[^142]` entry.

## Comments
- 2026-10-01 (developer, via agent): Decision: footnote 142 is abandoned. It belongs to no Essay and is removed from both V.1 and V.2. The developer is editing the output by hand for now.
