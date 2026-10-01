# 06: Footnotes opening with Chinese text on p. 1406 are merged into p. 1405's footnote (Essay V.2)

**What to build:** Page 1406 prints three footnotes whose text starts with Chinese characters straight after the number (`1八 十 老么 生 一 子…`, `2七 十 而 生…`, `3 Truyện kể rằng…`), matching body markers `mơ hồ[^1]`, `lý gì cả[^2]` and `奇 案[^3]`. They aren't recognized as numbered footnotes, so their text is merged into the continued `[^1]: (Trang 1405-1406)` entry and Part 3 Section V Essay 2 has no p. 1406 definitions. Each becomes its own `[^N]: (Trang 1406)` entry. Found by the ticket 02 validation report.

**Blocked by:** None

**Status:** ready-for-agent

- [ ] `PHAN_THU_BA/V_THU_TIM_NGUON_GOC_TRUYEN_CO_TICH_VIET_NAM/essay_02.md` has `[^1]`, `[^2]` and `[^3]` entries for p. 1406, and p. 1405's `[^1]` ends where its own text ends.
- [ ] The validator no longer flags Essay V.2 `ORPHAN_MARKER:1@1406` / `2@1406` / `3@1406`.
- [ ] A test pins p. 1406. Every other leaf's Markdown is unchanged (diff against the pre-change output).

## Comments
