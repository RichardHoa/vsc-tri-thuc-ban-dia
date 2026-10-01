# 05: Numbers inside a footnote on p. 1399 split it into extra footnotes (Essay V.2)

**What to build:** Page 1399's footnote 1 (`Đinh Gia Khánh trong Sơ bộ tìm hiểu…`) contains a count list (`… 2 U-gua, 1 Triều-tiên, 5 Việt-nam, … Cham-pa, 1 Khơ-me, 1 của dân tộc Y…`). The footnote splitter takes `2 U-gua` and a later `3` as new footnotes, so Part 3 Section V Essay 2 renders bogus `[^2]: (Trang 1399) U-gua, 1 Triều-tiên, 5 Việt-nam,` and `[^3]: (Trang 1399) Cham-pa, …` entries that have no body markers. The footnote stays one entry. Found by the ticket 02 validation report.

**Blocked by:** None

**Status:** ready-for-agent

- [ ] `PHAN_THU_BA/V_THU_TIM_NGUON_GOC_TRUYEN_CO_TICH_VIET_NAM/essay_02.md` has a single `[^1]: (Trang 1399)` entry holding the whole list.
- [ ] The validator no longer flags Essay V.2 `ORPHAN_FOOTNOTE:2@1399` / `ORPHAN_FOOTNOTE:3@1399`.
- [ ] A test pins p. 1399. Every other leaf's Markdown is unchanged (diff against the pre-change output).

## Comments
