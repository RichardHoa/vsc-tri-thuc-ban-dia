# Add "Kho Tàng Truyện Cổ Tích Việt Nam" collection (local-only, no Strapi changes)

## Context

The PR must add a new collection card — "KHO TÀNG TRUYỆN CỔ TÍCH VIỆT NAM" (Nguyễn Đổng Chi), cover `book.jpg` — to `/our-collections` on the `digitizing-vietnam-website` frontend, without touching the Strapi CMS. Clicking it opens a reading UI modeled on `our-collections/tho-ho-xuan-huong/tinh-hoa-mua-xuan`: a left panel listing all stories (with search + section filter I–X) and a right panel rendering the selected story's markdown, with footnotes that open a citation popover (same interaction as the Hán-Nôm dictionary lookup on that page).

The **real, already-extracted book content** lives in this repo (`vsc-tri-thuc-ban-dia`) at `extracted_stories/`: 10 section folders (`I_NGUON_GOC_SU_VAT` … `X_TRUYEN_VUI_TUOI_DI_DOM`), 201 `story_NNN.md` files total (~4 MB), each section with a `table_of_contents.json` that already is the manifest we need (story number, title, page range, markdown filename, `has_khao_di`, `footnote_count`). No placeholder content is needed — this real data gets copied into the frontend.

Research findings that shape this plan:
- **Every existing "local" collection** in the frontend (`han-nom-collection`, `vietnamese-edicts`, `the-borgia-tonchinensis-collection`) still requires a Strapi row for its `/our-collections` listing tile — only the *item list inside* the collection is local. Since we must avoid Strapi entirely, this PR introduces a **new pattern**: injecting one synthetic `Collection` object directly in `src/app/[locale]/our-collections/page.tsx`. This must be clearly commented as a temporary stopgap for this PR, to be replaced by a real Strapi entry later.
- On `tinh-hoa-mua-xuan`, "click a Hán-Nôm character" is a **Radix `Popover`** (shadcn `src/components/ui/popover.tsx`), animated via Tailwind's `animate-in`/`zoom-in-95`/`data-state` utilities (no framer-motion, no Sheet/Drawer). Footnotes will reuse that exact Popover component.
- No search/filter sidebar exists anywhere yet in `our-collections` — new, purpose-built for this page.
- The page header (title + abstract) on `tinh-hoa-mua-xuan` is rendered by the shared `[collectionid]/[documentid]/page.tsx`, fed by Strapi. Since this collection has no Strapi record, it gets its **own route** (`.../kho-tang-truyen-co-tich-viet-nam/[itemid]/page.tsx`, mirroring `han-nom-collection/[itemid]/page.tsx`) with a **locally-defined, dummy-text header** for now (per user instruction — real header copy comes later).
- **Footnote numbering is per-PDF-page, not per-story**: labels like `[^1]` repeat many times within one file (verified in `story_002.md`: six `[^N]` refs in the body — five labeled `[^1]`, one `[^2]` — matched one-to-one, in document order, against six defs in `### Chú thích`, also five `[^1]:` + one `[^2]:`). Label-based footnote matching (matching `[^1]` refs to `[^1]:` defs by their shared label, the way common markdown footnote extensions work) would silently collapse all same-labeled refs onto one definition. **This must be handled with custom, position-based matching** (the k-th `[^N]` marker in reading order pairs with the k-th definition in the `### Chú thích` list), done in our own `parseStoryMarkdown` function rather than any markdown library's footnote handling.
- Verse is already rendered as Markdown blockquotes (`> line` per verse line) by the extraction pipeline (`extractor/formatters.py`), including inside footnote definitions that contain verse. A custom `blockquote` renderer covers "poem format" for both body and footnote content.
- No markdown renderer is installed in `digitizing-vietnam-website`, and none is added. The extraction pipeline (`extractor/formatters.py` in this repo) only ever emits a narrow, known markdown subset for this content: `#`/`##`/`###` headings, plain-text paragraphs (no inline bold/italic/links), `> `-prefixed blockquote lines for verse, and `[^N]:` footnote definitions (optionally with indented verse continuation lines) — no tables, no strikethrough, no arbitrary inline links. That subset is small enough to hand-write a block-splitting function plus a tiny inline-link matcher (for the `[k](#fn-idx)` footnote-reference syntax we ourselves generate in step 4) directly in `StoryMarkdown.tsx`, so no markdown-rendering dependency is needed.
- `book.jpg` currently sits at `digitizing-vietnam-website/book.jpg` (repo root) and must move under `public/` to be servable by `next/image`.

## Data Layout (frontend repo: `digitizing-vietnam-website`)

```
public/
  images/collections/book.jpg
  data/kho-tang-truyen-co-tich-viet-nam/
    I_NGUON_GOC_SU_VAT/
      table_of_contents.json
      story_001.md ... story_025.md
    II_SU_TICH_DAT_NUOC_VIET/ ... X_TRUYEN_VUI_TUOI_DI_DOM/    # same shape, copied verbatim
                                                                  # from vsc-tri-thuc-ban-dia/extracted_stories/

src/app/[locale]/our-collections/kho-tang-truyen-co-tich-viet-nam/
  _data/
    index.ts              # server-only (fs/path): getStoryEntries(), getSections(), getStoryBySlug(slug)
                           # aggregates the 10 table_of_contents.json files — no hand-written manifest
  _lib/
    parseStoryMarkdown.ts # splits raw .md into {bodyMarkdown, footnotes: string[]}, position-matches
                           # [^N] refs -> defs, rewrites refs to `[k](#fn-{idx})` markdown links
    renderStoryBlocks.tsx # hand-written renderer for this corpus's markdown subset (h1/h2/h3,
                           # paragraph, blockquote/verse, footnote-link) -> React nodes; no dependency
  _components/
    KhoTangTruyenReader.tsx   # "use client": left search+filter+list, right <StoryMarkdown/>, ?story= param
    StoryMarkdown.tsx         # hand-written block parser (h1/h2/h3/blockquote/paragraph) + inline
                              # footnote-link matcher; no markdown-rendering dependency
    FootnotePopover.tsx       # Radix Popover citation bubble, reuses src/components/ui/popover.tsx
  [itemid]/
    page.tsx              # local Strapi-free header (dummy title/abstract) + breadcrumb + reader
```

## Implementation Steps

1. **Move cover image**: `book.jpg` → `digitizing-vietnam-website/public/images/collections/book.jpg`.

2. **Copy real data**: copy `vsc-tri-thuc-ban-dia/extracted_stories/` wholesale into `digitizing-vietnam-website/public/data/kho-tang-truyen-co-tich-viet-nam/`, preserving the 10 section folders and their `table_of_contents.json` + `story_*.md` files unchanged.

3. **`_data/index.ts`**: server-only module using Node `fs`/`path` (`path.join(process.cwd(), "public/data/kho-tang-truyen-co-tich-viet-nam", ...)`) to read all 10 `table_of_contents.json` files and flatten into `StoryEntry[]`: `{ slug (= markdown_file basename, e.g. "story_062" — globally unique), sectionId ("I".."X"), sectionTitle, storyNumber (local), title, mdPath, hasKhaoDi, footnoteCount }`. Exposes `getStoryEntries()`, `getSections()` (ordered I→X with titles + counts), `getStoryBySlug(slug)`.

4. **`_lib/parseStoryMarkdown.ts`**: pure function `parseStoryMarkdown(raw: string): { bodyMarkdown: string; footnotes: string[] }`.
   - Splits `raw` on the `\n---\n### Chú thích\n` delimiter (present whenever `footnote_count > 0`; absent entries pass through untouched).
   - Parses the footnote section into an ordered array of raw markdown chunks: a new entry starts at `^\[\^(\d+)\]:\s?(.*)$`; subsequent lines (verse continuation, 4-space indented per `formatters.py`) are dedented and appended to the current entry until the next `[^N]:` line or EOF.
   - In the body+`KHẢO DỊ` text, replaces every `[^\d+]` marker in document order with `[${i+1}](#fn-${i})` (0-based `i` tracked via closure, guarded so an unmatched marker past the parsed defs array length is left as plain text rather than a dead link).
   - This is unit-testable in isolation against a couple of real files from `extracted_stories/` (e.g. `story_002.md`'s known 6-ref/6-def case) — add a small test if the repo's test setup makes that cheap, otherwise verify manually per the Verification section.

5. **`_lib/renderStoryBlocks.tsx`**: a small hand-written function `renderStoryBlocks(markdown: string, footnotes: string[]): React.ReactNode[]` that covers exactly the markdown subset this corpus produces — no new dependency:
   - Split `markdown` into blocks on blank lines.
   - A block whose first line starts with `# `/`## `/`### ` renders as `h1`/`h2`/`h3`.
   - A block whose every line starts with `> ` renders as the verse/blockquote panel (strip the `> ` prefix per line).
   - Any other block renders as a paragraph (`p`).
   - Within a paragraph or blockquote line, run a small inline matcher for the exact `[k](#fn-idx)` footnote-link syntax produced in step 4 (regex `/\[(\d+)\]\(#fn-(\d+)\)/g`) — text outside those matches is emitted as plain text nodes, matches are emitted as `<FootnotePopover index={idx} content={footnotes[idx]} />`. No other inline markdown syntax (bold/italic/links/tables) exists in this corpus, so none is handled.

6. **`StoryMarkdown.tsx`** (`"use client"`): takes `{ bodyMarkdown, footnotes }`, calls `renderStoryBlocks(bodyMarkdown, footnotes)` and wraps the result:
   - `h1`/`h2`/`h3` → Merriweather, `text-branding-brown`, sizes matching the site's existing heading convention (`text-2xl`/`text-[32px]` per `tinh-hoa-mua-xuan`/`page.tsx`).
   - blockquote/verse block → `bg-branding-gray rounded-lg p-4`, each line its own `<div>`, no default quote-mark styling — the "nice poem format."
   - paragraph block → `font-['Helvetica Neue'] font-light text-xl` body text, matching `tinh-hoa-mua-xuan`.
   - footnote link → small superscript numeral styled `text-branding-brown underline cursor-pointer`, rendered via `<FootnotePopover/>` per the inline matcher above.

7. **`FootnotePopover.tsx`**: wraps `src/components/ui/popover.tsx` (`Popover`/`PopoverTrigger`/`PopoverContent`); content is the footnote's own markdown re-rendered through the same `renderStoryBlocks` function (so a footnote containing verse still gets the verse panel styling). Inherits the same `animate-in`/`zoom-in-95` open/close animation already used for the Hán-Nôm dictionary lookup, matching the interaction the user referenced.

8. **`KhoTangTruyenReader.tsx`** (`"use client"`, `?story=` searchParam like `tinh-hoa-mua-xuan`'s `?topic=`):
   - Left `<aside>`: search `<input>` (client-side substring match on story title), a section filter (Radix `Select` or `Tabs`: "Tất cả" + I–X using `getSections()` titles), and a `ScrollArea` list of matching stories grouped by section, reusing the `NavLink`-style active/hover treatment from `searchable-text/NavLink.tsx`.
   - Right panel: `<StoryMarkdown/>` for the currently selected story (parsed server-side, see step 9), falling back to the first story (`story_001`) if none selected. Clicking a story updates the URL via `router.replace` (same pattern `CollectionView.tsx` uses for tab state), keeping selection linkable/shareable.

9. **`[itemid]/page.tsx`**: server component, mirrors `han-nom-collection/[itemid]/page.tsx`'s shape but simpler. Resolves the selected story from `searchParams.story` (or defaults), reads its `.md` via `fs` from `public/data/...`, runs `parseStoryMarkdown`, and passes the result into `<KhoTangTruyenReader/>` along with `getStoryEntries()`/`getSections()` for the left panel. Renders breadcrumb + a locally-defined header block styled like the Strapi-driven one in `[collectionid]/[documentid]/page.tsx` (Merriweather 32px title, light 16px subtitle) filled with **dummy placeholder Vietnamese sentences** per user instruction, a `Separator`, then the reader. Comment clearly that title/abstract are placeholders pending real copy.

10. **Wire into `/our-collections` listing** (`src/app/[locale]/our-collections/page.tsx`): after the Strapi fetch/map, push one synthetic `Collection`-shaped object (title "Kho Tàng Truyện Cổ Tích Việt Nam", abstract = dummy sentence, `thumbnail.formats` pointing at `/images/collections/book.jpg` for every size key so `getImageByKey` resolves, `slug: "kho-tang-truyen-co-tich-viet-nam"`, `collection_categories: []` so it falls into the existing "Uncategorized" tab bucket, other array fields empty). Wrap in a prominent comment:
    ```ts
    // TEMPORARY (PR scope): this collection has no Strapi entry yet.
    // Remove this block once "kho-tang-truyen-co-tich-viet-nam" exists as a real
    // Strapi `collections` record with its own thumbnail/categories/abstract.
    ```

11. **Collection-detail route bypass**: `src/app/[locale]/our-collections/[collectionid]/page.tsx` will be hit if a user navigates to `/our-collections/kho-tang-truyen-co-tich-viet-nam` (the listing tile's link target). Add this slug to that file's static-slug bypass (same treatment as `han-nom-collection` et al.) so it skips the Strapi `collection_items` fetch and instead renders a small local view (dummy header + a single card/link into `[itemid]/page.tsx`). Comment this as temporary too.

## Verification

- `npm run dev` in `digitizing-vietnam-website`, visit `/vi/our-collections` — confirm the new card renders with the book cover, under "Uncategorized" (or whatever bucket empty categories land in), in grid/list/TOC view modes.
- Click through to the collection detail, then into the reader item page — confirm left panel lists all 201 stories grouped/filterable by section I–X, search narrows the list, clicking a story updates the right panel and the URL `?story=`.
- Open `story_002` specifically (known 6-ref/6-def case) and confirm all six footnote markers render as distinct clickable numerals `[1]`…`[6]`, each opening a Popover with its own distinct citation text (not all six collapsing onto the same definition) — this is the key correctness check for the position-based footnote matching.
- Confirm a story with verse (e.g. one with a `> ` blockquote in the source `.md`) renders as a distinct poem panel, not default browser blockquote styling, both in the body and inside a footnote's popover if applicable.
- Confirm footnote Popover open/close animation visually matches the existing Hán-Nôm dictionary popover on `tinh-hoa-mua-xuan`.
- `npm run lint` passes on new/changed files.
- Grep for `book.jpg` to confirm no remaining reference to the old repo-root path.
