# 03: Footnote 2 on p. 44 is merged into footnote 1 (Essay I.1)

**What to build:** Page 44 prints two footnotes in its footer: `1 a) Những truyện thuộc về cái lối cổ tích…` (several lines, ending `…Thăng Long xuất bản, 1952).`) and `2 Hợp tác xã Văn hóa mới xuất bản, Thanh-hóa, 1951; tr.92.` (y 727). Part 1 Section I Essay 1 renders only `[^1]: (Trang 44) …`, and footnote 2's text is folded into it, so the body marker `Việt-nam[^2]` has no definition. Each printed footnote becomes its own `[^N]` entry. Found by the ticket 02 validation report. Glossary: `CONTEXT.md`.

**Blocked by:** None

**Status:** resolved

- [ ] `PHAN_THU_NHAT/I_BAN_CHAT_TRUYEN_CO_TICH/essay_01.md` has `[^2]: (Trang 44) Hợp tác xã Văn hóa mới xuất bản, Thanh-hóa, 1951; tr.92.`, and `[^1]` on p. 44 no longer contains that text.
- [ ] The validator no longer flags Essay I.1 `ORPHAN_MARKER:2@44`.
- [ ] A test pins p. 44's two footnotes. Every other leaf's Markdown is unchanged (diff against the pre-change output).

## Comments
- 2026-10-02 (developer, via agent): Resolved manually by the developer (output edited by hand).
