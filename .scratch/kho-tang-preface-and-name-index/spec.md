# Kho Tàng reader — Preface and Story Name Index search

**Status:** ready-for-agent

Repos: `digitizing-vietnam-website` (reader, published data) and `vsc-tri-thuc-ban-dia` (one-off Story Name Index builder). Glossary: the website's `CONTEXT.md` (Book, Part, Section, Story, Essay, Part Introduction, **Preface**, Entry, Khảo dị, Footnote, **Story Name Index**, **Index Name**).

The extraction output folder in this repo was deliberately deleted; the hand-corrected copy published in the website is the only source of Book text. Do not recreate the extracted folder.

## Problem Statement

The Kho Tàng reader leaves out two parts of the printed book that readers need.

First, the author's *Lời nói đầu* (PDF pages 21–22), which explains the purpose and the three-Part structure of the whole Book, is not in the reader. A reader opens straight onto Phần thứ nhất, Essay 1, without the author's framing.

Second, a reader looking for a tale by name can only search Entry titles. Most tale names in the Book are not Entry titles. They appear only inside a Story's Khảo dị (variants from other regions and peoples) or in a Footnote. The printed book solves this with its *Bảng tra cứu tên truyện* (PDF pages 1518–1551): about 800 names in alphabetical order, each pointing to a Story number, a Tập and a location. The reader has no equivalent. Even after a reader finds the right Story, the name may be buried somewhere in a long Khảo dị. The printed index also has typos: it prints *A-đao dũng cảm* where Story 182 says *A-dao dũng cảm*.

## Solution

**Preface.** Lời nói đầu becomes the Book's Preface: its own Entry at `?muc=loi-noi-dau`, labelled "Lời nói đầu". It is listed first under the Phần thứ nhất tab and comes first in book order. The Book opens on it, and its "next" is Phần thứ nhất, Essay 1. Its text follows the printed page: 1957 spelling kept, paragraphs rejoined, and the place/date line and signature right-aligned.

**Story Name Index search.** The existing contents search box also matches Index Names. Results come in two groups: Entry titles first, then Index Names. Each Index Name result shows the name, an optional grey qualifier, the Story it points to, and where in that Story it occurs (the Story itself, Khảo dị or Chú thích). Clicking a result opens the Story with `?muc=truyen-N&ten=<name>`. Every occurrence of the name in the Story is highlighted in yellow, and the reader is scrolled to the right place. The spelling highlighted is the one in the Story text, not the printed index's spelling.

## User Stories

1. As a reader, I want to read the author's Lời nói đầu, so that I understand the purpose and structure of the Book before reading it.
2. As a reader, I want the Book to open on Lời nói đầu, so that I start where the printed book starts.
3. As a reader, I want Lời nói đầu listed first under the Phần thứ nhất tab, so that I can find it again from the contents panel.
4. As a reader, I want Lời nói đầu labelled "Lời nói đầu" and not "Lời dẫn", so that it isn't confused with a Part Introduction.
5. As a reader on Lời nói đầu, I want "next" to take me to Phần thứ nhất, Essay 1, so that I can read on in book order.
6. As a reader on Phần thứ nhất, Essay 1, I want "previous" to take me back to Lời nói đầu.
7. As a reader, I want Lời nói đầu to have no "previous" link, so that I know it is the start of the Book.
8. As a reader, I want a shareable `?muc=loi-noi-dau` link, so that I can point someone to the preface.
9. As a reader, I want the place/date and signature right-aligned as in print, so that the preface reads like the original.
10. As a reader, I want the preface in its original 1957 spelling ("Việt-nam"), so that the text stays faithful to the source.
11. As a reader, I want to type a tale name into the existing search box and see matching Index Names, so that I can find tales that are not Entry titles.
12. As a reader, I want Entry title matches listed before Index Name matches, so that a Story whose title matches stays at the top.
13. As a reader, I want each Index Name result to show which Story it points to, so that I know where I am going before I click.
14. As a reader, I want each result to say whether the name is in the Story itself, its Khảo dị or a Chú thích, so that I know what kind of mention it is.
15. As a reader, I want search to ignore case and diacritics, so that typing "a dao dung cam" finds *A-dao dũng cảm*.
16. As a reader, I want search to find a name by either the printed index spelling or the in-text spelling, so that typing *A-đao* or *A-dao* both work.
17. As a reader, I want a name that points to several Stories (*Xử phiến đá* → 110 and 120) to show one result per Story, so that I can choose which mention to open.
18. As a reader, I want same-named tales told apart by a grey qualifier (*Ba anh em* · *truyện Triều Tiên* vs *truyện Pháp*), so that I can pick the right one.
19. As a reader, I want a *Xem X* cross-reference name (*Cao phi viễn tẩu*) to lead to X's Story, so that alternative names still work.
20. As a reader, I want clicking an Index Name result to open its Story, so that I can read the tale.
21. As a reader, I want every occurrence of the name in the opened Story highlighted in yellow, so that I can see all its mentions.
22. As a reader, I want the page to scroll to the first occurrence, so that I don't have to hunt for it in a long Khảo dị.
23. As a reader, I want the highlight to use the Story text's spelling, so that names misspelled in the printed index (*A-đao*) still highlight correctly (*A-dao*).
24. As a reader, I want the qualifier left out of the highlight, so that *Ba anh em, truyện Pháp* highlights "Ba anh em" as written in the text.
25. As a reader, I want only the whole name highlighted, so that searching *A-dao dũng cảm* doesn't highlight every bare *A-dao*.
26. As a reader, I want highlighting to ignore case, so that a name highlights both in an uppercase heading and in mixed-case prose.
27. As a reader, I want highlighting to respect diacritics, so that *Ba anh em* doesn't highlight *bà anh em*.
28. As a reader, I want highlighting to tolerate small differences in spaces and hyphens, so that *A-dao* matches *A - dao*.
29. As a reader opening a Chú thích name, I want to be scrolled to that Footnote's marker with its popover open and the name highlighted inside, so that I land on the mention the index points to.
30. As a reader opening a Chú thích name that also appears earlier in the body, I want to still land on the Footnote, so that the index's location wins.
31. As a reader, I want a Footnote marker coloured yellow when its hidden text contains the name, so that I know to open it.
32. As a reader, I want the name highlighted when I open such a Footnote, so that I can find it inside.
33. As a reader, I want the highlight to survive a reload and be in the URL (`&ten=`), so that I can share a link that lands on the mention.
34. As a reader, I want the highlight to clear when I open another Entry, so that it doesn't carry over to unrelated text.
35. As a reader opening an Index Name the build couldn't find in the Story text, I want the Story to open at the top with no highlight, so that I still reach the right tale.
36. As the maintainer, I want a report of every Index Name the builder couldn't resolve against the Story text, so that I can fix those records by hand.
37. As the maintainer, I want the Story Name Index stored as one editable JSON file in the published data, so that I can correct names without re-running anything.
38. As the maintainer, I want the builder to read only the published website copy of the Story text, so that it never depends on the deleted extracted folder.
39. As the maintainer, I want the Preface wired through the table of contents (a top-level `preface` field), not a hardcoded path, so that the Book's structure stays data-driven.

## Implementation Decisions

**Preface**
- New published markdown file for Lời nói đầu, written by hand from PDF pages 21–22: the font's `ñ` replaced with `đ`, line breaks rejoined into paragraphs, 1957 spelling kept. The place/date line and the signature are marked so they render right-aligned. Use whatever block mechanism the Story markdown renderer already supports, or add a minimal one.
- `table_of_contents.json` gets a top-level `preface` field: `{ "title": "Lời nói đầu", "markdown_file": <path relative to data root>, "footnote_count": 0 }`.
- The reader's data accessor gains a new Entry kind, `"preface"`, with slug `loi-noi-dau`. It is placed first in book order. It is shown in the Phần thứ nhất division as an item before any Section, and it is distinct from the division's `introduction` (Phần thứ nhất still has none). The default Entry and the fallback for an unknown `?muc=` become the Preface.
- The contents panel labels the Preface by its own title, never by the "Lời dẫn" introduction label. Entry-title search matches it like any other Entry.

**Story Name Index builder (one-off, vsc-tri-thuc-ban-dia)**
- Input: PDF pages 1518–1551 and the website's published Story markdown folder (path passed in). Output: the index JSON written into the website's published Kho Tàng data, plus an unresolved-names report printed and/or written next to it.
- Parsing: the page layout is one column of tokens per record: name (may wrap across lines), location marker (`Khảo dị`, `Chú thích`, or blank), `số`, number, `tập`, Roman numeral. Handle a wrapped name, a `, <qualifier>` suffix on its own line, a `Xem <name>` cross-reference with no number, and a continuation record with no name (inherits the previous name: *Xử phiến đá* → 110 and 120). Skip the page heading and the intro paragraph on page 1518, and skip page numbers. Replace `ñ` with `đ`.
- Resolving: for each (name, Story) pair, search that Story's markdown for the name: first an exact match, ignoring case, with whitespace and hyphens loosened; then a match that also ignores diacritics and treats đ/d alike; then a fuzzy match over windows of the same word count, with a conservative threshold. When it is found, store the in-text spelling. Otherwise mark the record unresolved. When a Chú thích-located name is resolved, also record which Footnote holds it (the Footnote's label/ordinal as the reader identifies Footnotes), so the reader can open the right popover.
- Index JSON record shape (schema decision):

  ```ts
  interface IndexName {
    printed: string;        // as printed, đ-fixed, qualifier stripped
    qualifier?: string;     // "truyện Pháp"
    aliasOf?: string;       // set for "Xem X" lines; targets copied from X
    targets: {
      story: number;
      tap: "I" | "II" | "III" | "IV" | "V";
      location: "story" | "khao-di" | "chu-thich";
      textName?: string;    // in-text spelling; absent = unresolved
      footnote?: string;    // chu-thich only: which Footnote holds it
    }[];
  }
  ```

- The JSON is the source of truth after generation: the maintainer fixes unresolved records by hand. Re-running the builder would overwrite those fixes, so it is a one-off and not part of the website build.

**Reader: search**
- The data accessor loads the index JSON on the server and passes a compact list to the reader alongside the divisions.
- The existing search box filters Index Names on the existing normalised-text helper, matching against both `printed` and `textName`. Results render as a second group under the Entry-title groups, one row per (Index Name, target). Each row shows the name, a grey qualifier, the Story number and title, and a location label. Interface strings are localised (vi/en) like the rest of the reader.

**Reader: highlight**
- A new search param, `ten`, carries the name to highlight: the in-text spelling, or nothing for an unresolved target. A second param is needed to say "scroll to Footnote X" for Chú thích targets. Selecting another Entry from the panel or with previous/next drops both params.
- One pure matcher function takes text and a name and returns match ranges. It ignores case, matches diacritics exactly, loosens whitespace and hyphens, and only matches the whole name. The renderer uses it to wrap matches in a yellow `<mark>` across the Story body, headings, Khảo dị and Footnote bodies.
- Scrolling: for a Chú thích target, scroll to the target Footnote's marker and open its popover. Otherwise scroll to the first `<mark>` in document order.
- A Footnote marker whose body contains a match gets a yellow style. Popovers are not opened automatically, except for the target Footnote of a Chú thích result.

## Testing Decisions

- Keep tests minimal: test only the important functions and their real edge cases. Aim for a handful of cases, not exhaustive coverage. Test external behaviour (inputs → outputs), not internal structure.
- **Index builder (pytest, vsc-tri-thuc-ban-dia), one seam:** the builder's single entry point, taking index page text and a Story folder and returning records plus unresolved names. Fixture index text and a tiny fixture Story folder should cover: the *A-đao* → *A-dao* typo resolution, a qualifier (*Ba anh em, truyện Pháp*), a *Xem* alias, a nameless continuation record (two targets), a wrapped name, and one deliberately unresolvable name. Prior art: `tests/test_pipeline.py`, `tests/test_footnotes.py`.
- **Website:** no test runner and none is added (same decision as the earlier Kho Tàng reader spec). Verification is type-check, lint, and this manual checklist against `next dev`:
  - The default reader URL opens on Lời nói đầu. It is first under the Phần 1 tab, labelled "Lời nói đầu", has no "previous", and "next" goes to Phần 1 Essay 1, whose "previous" comes back. The signature is right-aligned. `?muc=bogus` falls back to the Preface.
  - Searching "a dao" lists *A-dao dũng cảm* → Story 182 (Khảo dị). Clicking it highlights every *A-dao dũng cảm* in Story 182 and scrolls to the first. A bare *A-dao* is not highlighted.
  - Searching "ba anh em" shows separate rows with qualifiers *truyện Triều Tiên* (61) and *truyện Pháp* (107). Each highlights "Ba anh em" in its Story.
  - *Xử phiến đá* shows two rows (110, 120). *Cao phi viễn tẩu* leads to *Giáp Kén-xã Nhộng*'s Story.
  - A Chú thích name (e.g. *Chiếc nhẫn thần*) scrolls to its Footnote marker with the popover open and the name highlighted.
  - A Story-location name that also occurs in a Footnote shows that marker in yellow.
  - Reloading keeps the highlight. Clicking another Entry clears it.
  - An unresolved record opens its Story at the top with no highlight.
  - Narrow viewport: the search results and highlight work with no horizontal scroll.

## Out of Scope

- A browsable A–Z tab for the Story Name Index (the JSON makes it easy to add later).
- Re-running or recreating the extraction pipeline or the extracted folder.
- Indexing names from Phần 1, Phần 3 or the Bibliography; the printed index covers only Phần thứ hai.
- Correcting the Story text to match the printed index; the text is the authority.
- Highlighting from free-text search (only Index Name results set `ten`).
- Adding a JavaScript test runner to the website.

## Further Notes

- In this PDF the font maps `đ` to `ñ` everywhere. The index's *A-đao* is a genuine misprint of the text's *A-dao*, not an encoding artifact.
- Of roughly 800 index records, about 600 point to a Khảo dị and about 9 to a Chú thích; the rest point to the Story itself.
- `Tập` is shown for information only. Story numbers are unique across the Book, so `story` alone identifies the target.
