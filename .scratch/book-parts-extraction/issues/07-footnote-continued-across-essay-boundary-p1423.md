# 07: A footnote continued from p. 1423 lands in the next Essay (Essays V.3 / V.4)

**What to build:** A footnote that starts on p. 1423 (the last page of Part 3 Section V Essay 3) continues at the top of p. 1424's footer (`thuyết An-nam. Sự so sánh này không thuyết phục được tôi"…`). Essay 4 starts on p. 1424, so the continuation is kept there as a `continued` `[^1]: (Trang 1424)` entry with no marker, and Essay 3's footnote is cut short. The continuation belongs to the footnote it continues: Essay 3 renders it merged as `(Trang 1423-1424)`, and Essay 4 doesn't carry it. This needs a rule for continuations that run past a leaf's last page. Found by the ticket 02 validation report.

**Blocked by:** None

**Status:** resolved

- [ ] Essay V.3's footnote reads through to the end of its p. 1424 continuation, as one `(Trang 1423-1424)` entry.
- [ ] Essay V.4 has no unmarked `[^1]: (Trang 1424)` entry, and the validator no longer flags it `ORPHAN_FOOTNOTE:1@1424`.
- [ ] Tests cover a footnote continued past a leaf's last page. No Story's Markdown changes unless a Story has the same case (check the diff).

## Comments
- 2026-10-01 (agent): Wider than described. The footnote is V.3's `[^2]`, which starts on p. 1422 and runs over all of p. 1423 (footnote-size text only, no separator) into the top of p. 1424's footer. All of p. 1423's text is rendered in V.3's **body** (`essay_03.md` lines 63–83, `Đông Á có kể ra…` through `…của truyền`). It isn't flagged, because coverage stays 1.000. The fix must append p. 1423 and the p. 1424 head to `[^2]` as `(Trang 1422-1424)`.
- 2026-10-02 (developer, via agent): Resolved manually by the developer (output edited by hand).
