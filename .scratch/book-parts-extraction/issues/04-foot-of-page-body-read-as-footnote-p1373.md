# 04: Body paragraph at the foot of p. 1373 is read as a footnote (Essay IV.3)

**What to build:** Page 1373 has no drawn footnote separator and no footnotes. Its last body paragraph, `2. Trước hết, đối tượng đầu tiên được tác giả truyện cổ tích bênh vực…` (body size 13.7, y 710), falls below the fallback footer line and is rendered as `[^2]: (Trang 1373) Trước hết…` in Part 3 Section IV Essay 3, instead of body text in reading order. Body text stays body text when a page has no separator, and footer classification doesn't take a body-size numbered paragraph as a footnote. Found by the ticket 02 validation report.

**Blocked by:** None

**Status:** ready-for-agent

- [ ] `PHAN_THU_BA/IV_DAC_DIEM_CUA_TRUYEN_CO_TICH_VIET_NAM/essay_03.md` has the `2. Trước hết…` paragraph in the body, in reading order, and no `[^2]` definition for p. 1373.
- [ ] The validator no longer flags Essay IV.3 `ORPHAN_FOOTNOTE:2@1373`, and its rendered coverage stays 1.000.
- [ ] A test covers a body-size numbered paragraph at the foot of a page with no separator. No Story's Markdown changes (diff against the pre-change output).

## Comments
